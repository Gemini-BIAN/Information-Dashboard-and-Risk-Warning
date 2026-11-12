"""Immutable evidence revisions, deterministic assessments and namespace-scoped queries."""

import hashlib
import json
import re
from datetime import datetime, timedelta
from html import escape

from sqlalchemy import select

from scm.platform.contracts import Record
from scm.platform.models import Alert, Assessment, Audit, Evidence, Item, PlatformSource, Report, Review
from scm.settings import ROOT, TIMEZONE, utcnow

RULE_VERSION = "platform-2026-11-11.2"


def specs():
    return json.loads((ROOT / "config/platform_sources.json").read_text(encoding="utf-8"))


def register(session, configurations=None):
    for spec in configurations if configurations is not None else specs():
        row = session.get(PlatformSource, spec["id"])
        if row is None:
            row = PlatformSource(id=spec["id"], spec_json="{}")
            session.add(row)
        row.spec_json = json.dumps(spec, ensure_ascii=False)
    session.flush()


def company_name(value):
    config = json.loads((ROOT / "config/platform_companies.json").read_text(encoding="utf-8"))
    for company in config["companies"]:
        if value.strip().casefold() in {
            s.casefold() for s in [company["id"], company["name"], *company["aliases"]]
        }:
            return company["name"]
    return value.strip() or "unknown"


def assess(record, now=None):
    now = now or utcnow()
    text = record.title + "\n" + record.body
    signals = []
    for sentence in re.split(r"(?<=[.!?。])\s+|\n", text):
        if re.search(
            r"\b(cancelled|strike|closure|suspended|delayed|surcharge)\b|罢工|停工|延迟|附加费",
            sentence,
            re.I,
        ):
            if not re.search(
                r"\b(no|not|averted|resolved|may|could|possible)\b|没有|可能|已解除", sentence, re.I
            ):
                signals.append(sentence[:1200])
    age = (now - record.published_at).total_seconds() / 86400 if record.published_at else None
    history = age is not None and age > 30
    future = age is not None and age < -1
    level = "medium" if signals and not history and not future and age is not None else "unknown"
    from scm.content.relevance import relevance

    domain, event_type, business = relevance(record.title, record.body, record.published_at, now)
    relevant = business.decision
    if record.module == "capacity" and record.project_id and record.company != "unknown":
        relevant = "possibly_relevant"
    if record.module == "market" and (record.value is not None or record.route):
        relevant = "possibly_relevant"
    if relevant == "excluded":
        level = "unknown"
    return {
        "rule_version": RULE_VERSION,
        "risk_level": level,
        "relevance": relevant,
        "business_reasons": business.reasons_zh,
        "topic": event_type,
        "domain": domain,
        "risk_reason": "命中文内风险信号；仅待核实，不证明当前业务影响"
        if level == "medium"
        else "缺合格近期风险证据；未知不等于低风险",
        "signal_quotes": signals,
        "historical": history,
        "quality_flags": (["DATE_UNKNOWN"] if age is None else [])
        + (["HISTORICAL_NOTICE"] if history else [])
        + (["FUTURE_DATE_NEEDS_REVIEW"] if future else [])
        + ["CANDIDATE_NOT_BUSINESS_VERIFIED"],
        "facts": [{"quote": record.evidence_quote or record.body[:1000], "label": "原文摘录，非中文翻译"}],
        "impact": "若计划兑现或公告适用于相关产品/航线，可能影响供应布局与提前期；实际影响待核实。",
        "action": "核实公告日期、主体、适用范围及后续更正；计划产能不计为实际产能。",
        "provider": "rules-only; no LLM",
    }


def ingest(session, source_id, record, now=None):
    record = Record.model_validate(record)
    if not session.get(PlatformSource, source_id):
        raise ValueError("Unknown configured source")
    # Caller data cannot promote Live provenance. Only the adapter supplies it after actual guarded HTTP.
    source = json.loads(session.get(PlatformSource, source_id).spec_json)
    if record.mode == "live":
        from scm.platform.adapters import permission_gate

        permission_gate(source, utcnow())
        from urllib.parse import urlsplit

        if urlsplit(record.url).hostname != urlsplit(source["url"]).hostname:
            raise ValueError("Live evidence must stay on the approved source host")
    raw = record.model_dump(mode="json")
    comparable = {
        k: v
        for k, v in raw.items()
        if k != "fetched_at"
        and not (k in ["effective_at", "expires_at", "observed_at", "transport"] and v is None)
    }
    sha = hashlib.sha256(json.dumps(comparable, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    item = session.scalar(
        select(Item).where(
            Item.source_id == source_id, Item.external_id == record.external_id, Item.mode == record.mode
        )
    )
    if item:
        current = session.scalar(
            select(Evidence).where(Evidence.item_id == item.id, Evidence.version == item.version)
        )
        if current.sha256 == sha:
            return "unchanged", item
        if record.fetched_at < datetime.fromisoformat(current.captured_at):
            raise ValueError("Out-of-order capture rejected; cannot overwrite current revision")
        if item.module != record.module:
            raise ValueError("Cannot silently move an existing item across modules")
    else:
        item = Item(
            source_id=source_id,
            external_id=record.external_id,
            mode=record.mode,
            module=record.module,
            version=0,
            updated_at=utcnow().isoformat(),
        )
        session.add(item)
        session.flush()
    outcome = "inserted" if item.version == 0 else "updated"
    item.version += 1
    item.updated_at = (now or utcnow()).isoformat()
    item.review_status = "pending"
    evidence = Evidence(
        item_id=item.id,
        version=item.version,
        raw_json=json.dumps(raw, ensure_ascii=False),
        sha256=sha,
        captured_at=record.fetched_at.isoformat(),
    )
    session.add(evidence)
    session.flush()
    analysis = assess(record, now)
    session.add(
        Assessment(
            evidence_id=evidence.id,
            analyzed_at=utcnow().isoformat(),
            payload_json=json.dumps(analysis, ensure_ascii=False),
        )
    )
    if analysis["risk_level"] == "medium":
        session.add(
            Alert(evidence_id=evidence.id, mode=record.mode, created_at=utcnow().isoformat(), state="pending")
        )
    return outcome, item


def rows(session, mode, module=None, query="", country=None, risk=None, company=None):
    if mode not in ["live", "demo", "manual"]:
        raise ValueError("Explicit valid namespace required")
    result = []
    for item in session.scalars(select(Item).where(Item.mode == mode)):
        if module and item.module != module:
            continue
        ev = session.scalar(
            select(Evidence).where(Evidence.item_id == item.id, Evidence.version == item.version)
        )
        analysis = session.scalar(select(Assessment).where(Assessment.evidence_id == ev.id))
        raw = json.loads(ev.raw_json)
        raw["company"] = company_name(raw["company"])
        payload = assess(Record.model_validate_json(ev.raw_json))
        payload["display_as_of"] = utcnow().isoformat()
        payload["stored_analysis_at"] = analysis.analyzed_at
        payload["stored_rule_version"] = json.loads(analysis.payload_json)["rule_version"]
        if (
            (
                query
                and query.casefold()
                not in (raw["title"] + " " + raw["body"] + " " + raw["company"]).casefold()
            )
            or (country and raw["country"] != country)
            or (risk and payload["risk_level"] != risk)
            or (company and raw["company"] != company)
        ):
            continue
        result.append(
            {
                "id": item.id,
                "source_id": item.source_id,
                "source_confidence": json.loads(session.get(PlatformSource, item.source_id).spec_json).get(
                    "confidence", "unreviewed"
                ),
                "version": item.version,
                "review_status": item.review_status,
                "evidence_id": ev.id,
                "sha256": ev.sha256,
                "updated_at": item.updated_at,
                "raw": raw,
                "analysis": payload,
            }
        )
    return sorted(result, key=lambda r: (r["raw"]["published_at"] or "", r["id"]), reverse=True)


def review(session, item_id, mode, status, reason, actor):
    item = session.get(Item, item_id)
    if (
        not item
        or item.mode != mode
        or status not in ["confirmed", "rejected", "pending"]
        or not reason.strip()
        or not actor.strip()
    ):
        raise ValueError("Scoped item, review status, reviewer and reason required")
    item.review_status = status
    session.add(
        Review(
            item_id=item.id,
            version=item.version,
            created_at=utcnow().isoformat(),
            actor=actor.strip(),
            status=status,
            reason=reason.strip(),
        )
    )


def set_alert(session, alert_id, mode, state):
    alert = session.get(Alert, alert_id)
    if not alert or alert.mode != mode or state not in ["pending", "read", "handled"]:
        raise ValueError("Invalid scoped alert transition")
    alert.state = state


def generate_report(session, mode, kind="daily", day=None):
    if kind not in ["daily", "weekly"]:
        raise ValueError("daily/weekly required")
    local = (day or utcnow()).astimezone(TIMEZONE)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if kind == "weekly":
        start -= timedelta(days=start.weekday())
    end = start + timedelta(days=1 if kind == "daily" else 7)
    selected = [
        r
        for r in rows(session, mode)
        if r["review_status"] != "rejected"
        and r["analysis"]["relevance"] != "excluded"
        and r["raw"]["published_at"]
        and start <= datetime.fromisoformat(r["raw"]["published_at"]) < end
    ]
    # Explicit project IDs only; similar prose does not prove it is the same project.
    grouped = {}
    for r in selected:
        raw = r["raw"]
        key = (raw["module"], raw["company"], raw["project_id"]) if raw.get("project_id") else (r["id"],)
        grouped.setdefault(key, []).append(r)
    blocks = []
    for group in grouped.values():
        r = group[0]
        raw = r["raw"]
        blocks.append(
            f"<article><h3>{escape(raw['title'])}</h3><p>{escape(raw['module'])} · {escape(r['analysis']['risk_reason'])} · {len(group)}条关联记录</p><blockquote>{escape(raw['body'][:1000])}</blockquote><p>潜在业务影响（推测）：{escape(r['analysis']['impact'])}</p><p>待核实/建议：{escape(r['analysis']['action'])}</p>"
            + "".join(
                f'<p><a href="{escape(x["raw"]["url"], quote=True)}">原始证据</a> · 发布{escape(x["raw"]["published_at"])} · SHA256 {x["sha256"]} · {escape(x["source_id"])}</p>'
                for x in group
            )
            + "</article>"
        )
    port_summary = ""
    if mode in ["live", "demo"]:
        from scm.ports.service import snapshots

        states = snapshots(session, mode)
        port_summary = "<h2>12港口生成时状态（不是报告周期历史实况）</h2>" + "".join(
            f"<p>{escape(port)}：{escape(state['state'])} / {escape(state['severity'])}</p>"
            for port, state in states.items()
        )
    body = (
        f'<!doctype html><html lang="zh"><meta charset="utf-8"><title>ESCIM {kind}</title><body><h1>{mode.upper()} · ESCIM {kind}</h1><p>{start.date()} 至 {end.date()}（不含结束日） · Asia/Shanghai</p><h2>今日/本周重点与行业、产能及物流动态</h2>'
        + ("".join(blocks) if blocks else "<p>本期没有可报告的新增情报；不代表外部没有重要事件。</p>")
        + port_summary
        + "<h2>来源与数据质量</h2><p>覆盖不足；原发布日期不替换为采集日期。无LLM，仅原文摘录与中文规则模板。港口等待时间/AIS/ETA未知；计划产能不等于实际产能。未来1–3个月影响需核实，不做无证据预测。人工数据不视为已验证实时价格。</p><p>EU来源文字 © European Union，CC BY4.0；HHM文字按其显示信息许可。摘录与规则分析为本地处理，不取图片/Logo。</p></body></html>"
    )
    saved = session.scalar(
        select(Report).where(
            Report.mode == mode, Report.kind == kind, Report.period_start == start.isoformat()
        )
    )
    if saved is None:
        saved = Report(
            mode=mode, kind=kind, period_start=start.isoformat(), generated_at=utcnow().isoformat(), html=body
        )
        session.add(saved)
    else:
        saved.html = body
        saved.generated_at = utcnow().isoformat()
    session.flush()
    return saved


def audit(session, source_id, mode, payload):
    session.add(
        Audit(
            source_id=source_id,
            mode=mode,
            created_at=utcnow().isoformat(),
            payload_json=json.dumps(payload, ensure_ascii=False),
        )
    )
