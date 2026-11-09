import hashlib
import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from sqlalchemy import select

from scm.collectors.http import AccessBlocked
from scm.database.models import Analysis, PortAlert, PortSignal, Source
from scm.intelligence.providers import RuleProvider, configured_provider
from scm.intelligence.service import ingest
from scm.ports.engine import LEVELS, Notice, assess_notice
from scm.ports.registry import initial_snapshot, registry, source_specs
from scm.schemas import LLMAnalysis, RawArticle
from scm.settings import utcnow


def permission_gate(source, now):
    if (
        source.get("permission") != "allowed_full_text"
        or source.get("automatic_access_allowed") is not True
        or not source.get("audit_ref")
        or not source.get("terms_url")
    ):
        raise AccessBlocked(
            "NEEDS_PERMISSION: automatic access and text retention not confirmed; no requests"
        )
    verified = datetime.fromisoformat(source.get("permission_verified_at", ""))
    if verified.tzinfo is None or not now - timedelta(days=30) <= verified <= now:
        raise AccessBlocked("NEEDS_PERMISSION: permission audit expired")


def analyze(notice, assessment, provider=None):
    quote = notice.body[:1000]
    fallback = {
        "mode": "rules-fallback",
        "note": "未启用LLM或无凭据；中文规则模板与原文摘录，非全文翻译。",
        "summary_zh": "运营公告候选｜" + notice.title,
        "facts": [{"quote": quote, "label": "原文证据，未作语义翻译"}],
        "potential_impacts": [
            "若公告适用于相关港口、货物或承运人服务，复核截关、危险品接收与替代安排；具体影响待核实。"
        ],
        "tasks": [
            "核实公告有效期及是否被替代/取消。",
            "向承运人/货代确认电解液、危险品及ISO Tank适用条件；无证据不改ETA。",
        ],
    }
    if provider is None and os.getenv("SCM_PORT_LLM_ENABLED", "").lower() == "true":
        provider = configured_provider()
    if provider is None or provider.name == "rules-only":
        return fallback
    try:
        article = RawArticle(
            title=notice.title,
            body=notice.body,
            url=notice.url,
            source="port01",
            published_at=notice.published_at,
            fetched_at=notice.fetched_at,
            data_mode=notice.data_mode,
        )
        result = LLMAnalysis.model_validate(provider.analyze(article, {"event_type": "港口运营"}))
        if any(f.quote not in notice.body for f in result.facts):
            raise ValueError("Ungrounded quote")
        return {
            **fallback,
            "mode": "optional-llm",
            "note": "AI中文分析待审核；原文是事实依据，LLM不决定严重度、地点或状态。",
            "summary_zh": result.title_zh,
            "potential_impacts": result.potential_impacts,
            "tasks": result.suggested_actions,
        }
    except Exception as exc:
        return {**fallback, "note": "LLM不可用/证据校验失败，已规则降级：" + type(exc).__name__}


def store_notice(session, source, notice, now=None, provider=None):
    now = now or utcnow()
    if notice.data_mode == "live":
        permission_gate(source, now)
    elif not notice.external_id.startswith("DEMO-"):
        raise ValueError("Demo notice must be explicitly marked")
    parsed = urlsplit(notice.url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != urlsplit(source["url"]).hostname
        or parsed.username
        or parsed.password
        or parsed.port not in [None, 443]
    ):
        raise AccessBlocked("Unsupported notice origin")
    source_id = "port01-" + source["id"]
    row = session.get(Source, source_id)
    if row is None:
        row = Source(
            id=source_id, name=source["name"], url=source["url"], method="port-operational", enabled=False
        )
        session.add(row)
        session.flush()
    previous_signal = session.scalar(
        select(PortSignal).where(
            PortSignal.source_id == source_id,
            PortSignal.external_id == notice.external_id,
            PortSignal.data_mode == notice.data_mode,
        )
    )
    prior = json.loads(previous_signal.payload_json)["assessment"] if previous_signal else None
    assessment = assess_notice(notice, source["ports"], now, prior=prior)
    outcome, event = ingest(
        session,
        RawArticle(
            title=notice.title,
            body=notice.body,
            url=notice.url,
            source=source_id,
            published_at=notice.published_at,
            fetched_at=notice.fetched_at,
            data_mode=notice.data_mode,
        ),
        RuleProvider(),
    )
    signal = session.scalar(
        select(PortSignal).where(
            PortSignal.source_id == source_id,
            PortSignal.external_id == notice.external_id,
            PortSignal.data_mode == notice.data_mode,
        )
    )
    old = json.loads(signal.payload_json) if signal else None
    content = {
        "notice": notice.model_dump(mode="json"),
        "assessment": assessment,
        "ai": analyze(notice, assessment, provider),
        "source_ref": source["id"],
        "source_name": source["name"],
        "permission_audit": source.get("audit_ref", "DEMO"),
        "terms_url": source.get("terms_url"),
        "retention": "text only; no images/PDF; source-specific permission required",
    }
    signature = hashlib.sha256(
        json.dumps(
            {k: assessment[k] for k in ["ports", "kind", "severity", "lifecycle", "relevance"]}
            | {"from": content["notice"]["valid_from"], "until": content["notice"]["valid_until"]},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    changed = signal is None or signal.fingerprint != signature
    if signal is None:
        signal = PortSignal(
            source_id=source_id,
            external_id=notice.external_id,
            data_mode=notice.data_mode,
            event_id=event.id,
            payload_json="{}",
            fingerprint="",
            version=0,
            updated_at=now.isoformat(),
        )
        session.add(signal)
        session.flush()
    signal.event_id = event.id
    if changed:
        signal.version += 1
    signal.fingerprint, signal.payload_json, signal.updated_at = (
        signature,
        json.dumps(content, ensure_ascii=False),
        now.isoformat(),
    )
    row.last_checked_at = notice.fetched_at.isoformat()
    if notice.data_mode == "live" and notice.verification_type == "LIVE_HTTP":
        row.last_success_at = notice.fetched_at.isoformat()
        row.last_status = "PASS"
    if (
        changed
        and assessment["ports"]
        and assessment["kind"] != "unknown"
        and assessment["state"] != "stale"
        and (assessment["lifecycle"] != "resolved" or old)
    ):
        previous = old["assessment"] if old else None
        kind = "new"
        if previous:
            if assessment["lifecycle"] == "resolved" and previous["lifecycle"] != "resolved":
                kind = "resolution"
            elif LEVELS[assessment["severity"]] > LEVELS[previous["severity"]]:
                kind = "escalation"
            else:
                kind = "substantive_update"
        session.add(
            PortAlert(
                signal_id=signal.id,
                version=signal.version,
                event_id=event.id,
                data_mode=notice.data_mode,
                kind=kind,
                created_at=now.isoformat(),
                summary_json=json.dumps(content, ensure_ascii=False),
            )
        )
    # Module assessment is independent of existing article severity/lifecycle.
    latest = session.scalar(
        select(Analysis).where(Analysis.event_id == event.id).order_by(Analysis.id.desc())
    )
    payload = json.loads(latest.payload_json)
    payload["port01"] = content
    latest.payload_json = json.dumps(payload, ensure_ascii=False)
    session.flush()
    return outcome, signal


def snapshots(session, mode, now=None):
    now = now or utcnow()
    result = {p.id: initial_snapshot(p, now) for p in registry().ports}
    specs = {s["id"]: s for s in source_specs()}
    for snap in result.values():
        checks = [s.get("last_permission_check") for s in snap["coverage"] if s.get("last_permission_check")]
        snap["last_permission_check"] = max(checks, default=None)
        for coverage in snap["coverage"]:
            row = session.get(Source, "port01-" + coverage["id"])
            if row and mode == "live":
                snap["last_check"] = max(snap["last_check"] or "", row.last_checked_at or "") or None
                snap["last_success"] = max(snap["last_success"] or "", row.last_success_at or "") or None
    for signal in session.scalars(select(PortSignal).where(PortSignal.data_mode == mode)):
        data = json.loads(signal.payload_json)
        notice = Notice.model_validate(data["notice"])
        original = data["assessment"]
        assessment = assess_notice(notice, original["ports"], now, prior=original)
        # A failed/latest source check or revoked permission cannot remain current.
        if mode == "live":
            spec = specs.get(data["source_ref"], {})
            try:
                permission_gate(spec, now)
                src = session.get(Source, signal.source_id)
                if not src or src.last_status != "PASS":
                    raise AccessBlocked("Latest source check unsuccessful")
            except (AccessBlocked, ValueError):
                assessment = {
                    **assessment,
                    "state": "unknown",
                    "confidence": "permission_or_coverage_unverified",
                }
        for id in assessment["ports"]:
            snap = result[id]
            snap["events"].append(
                {**data, "assessment": assessment, "signal_id": signal.id, "version": signal.version}
            )
    for snap in result.values():
        events = snap["events"]
        current = [x for x in events if x["assessment"]["state"] == "confirmed_disruption"]
        normals = [x for x in events if x["assessment"]["state"] == "confirmed_normal"]
        if current:
            snap["state"] = "confirmed_disruption"
        elif normals:
            snap["state"] = "confirmed_normal"
        elif events and all(x["assessment"]["state"] == "stale" for x in events):
            snap["state"] = "stale"
        candidates = [
            x["assessment"]
            for x in events
            if x["assessment"]["lifecycle"] != "resolved" and x["assessment"]["state"] != "stale"
        ]
        if candidates:
            snap["severity"] = max((x["severity"] for x in candidates), key=LEVELS.get)
            snap["relevance"] = max((x["relevance"] for x in candidates), key=LEVELS.get)
        snap["events"].sort(key=lambda x: x["notice"]["published_at"] or "", reverse=True)
        if snap["state"] == "confirmed_disruption":
            snap["note"] = "有明确有效运营公告；仍需核对具体承运人服务、货类和码头。"
        elif snap["state"] == "confirmed_normal":
            snap["note"] = "仅在公告明确范围与时点内确认正常，不代表所有码头/后续时段。"
        elif snap["state"] == "stale":
            snap["note"] = "仅有过期证据；应重新核实，不延续旧风险为当前状态。"
    return result


def read_alert(session, alert_id, mode):
    alert = session.get(PortAlert, alert_id)
    if alert is None or alert.data_mode != mode:
        raise ValueError("Alert not found in current namespace")
    alert.read_at = utcnow().isoformat()
