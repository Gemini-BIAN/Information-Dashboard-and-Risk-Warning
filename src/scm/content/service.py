"""Phase 2A path reusing existing raw revisions, ingestion, rules and analyses."""

import json
from datetime import datetime, timedelta

from sqlalchemy import func, select

from scm.collectors.http import AccessBlocked
from scm.collectors.service import run_collection
from scm.content.contracts import (
    PRIORITIES,
    Applicability,
    EvidenceSnippet,
    FactualStatement,
    Inference,
    IntelligenceRecord,
    SuggestedAction,
)
from scm.content.relevance import VERSION, relevance
from scm.database.models import Analysis, Event, RawRevision
from scm.intelligence.providers import RuleProvider
from scm.settings import utcnow


def require_permission(spec, now):
    policy = spec.get("reuse_policy", {})
    if policy.get("permission") != "allowed_full_text" or policy.get("status") != "reviewed_allowed":
        raise AccessBlocked(
            "Phase 2A body permission not established; metadata/link only, no article requests"
        )
    verified = datetime.fromisoformat(policy.get("verified_at", ""))
    if verified.tzinfo is None or not now - timedelta(days=30) <= verified <= now:
        raise AccessBlocked("Permission evidence needs current review (30 days)")
    if not policy.get("notice_url") or not policy.get("evidence_ref"):
        raise AccessBlocked("Missing permission provenance")


def attach_content(session, spec, now):
    count = 0
    for event in session.scalars(
        select(Event).where(Event.source_id == spec["id"], Event.data_mode == "live")
    ):
        revision = session.scalar(
            select(RawRevision).where(
                RawRevision.event_id == event.id, RawRevision.content_hash == event.content_hash
            )
        )
        analysis = session.scalar(
            select(Analysis)
            .where(Analysis.event_id == event.id, Analysis.revision_id == revision.id)
            .order_by(Analysis.id.desc())
        )
        payload = json.loads(analysis.payload_json)
        if payload.get("content_rule_version") == VERSION:
            continue
        pub = datetime.fromisoformat(event.published_at) if event.published_at else None
        domain, kind, rel = relevance(event.title, revision.body, pub, now, event.lifecycle)
        ev_id = f"raw-{revision.id}"
        evidence = EvidenceSnippet(
            evidence_id=ev_id,
            source_url=revision.source_url,
            quote=revision.body[:1000],
            locator="#body text" if spec["parser"] == "hamburg" else "article + header description",
            raw_revision_id=str(revision.id),
            raw_sha256=revision.content_hash,
            capture_mode="live",
            precision_note="原文文字摘录，非语义翻译；hash为现有含标题/日期的revision内容指纹",
        )
        flags = ["RULE_TEMPLATE_NOT_TRANSLATION", "SOURCE_REVIEW_PENDING"]
        if spec["parser"] == "hamburg":
            flags += ["TIMEZONE_ASSUMED_EUROPE_BERLIN", "ORIGINAL_PUBLISHER_MAY_BE_THIRD_PARTY"]
        flags += rel.reason_codes
        impacts = {
            "A": "若公告实际影响相关港口或航路，复核交付提前期；当前未确认具体航次影响。",
            "B": "若法规适用于相关商品/主体，复核合规里程碑；电池义务不自动适用于电解液。",
            "C": "若产能计划兑现且与区域需求相关，可复核供应布局；公告不等于实际投产。",
        }
        previous = session.scalar(
            select(RawRevision)
            .where(RawRevision.event_id == event.id, RawRevision.id < revision.id)
            .order_by(RawRevision.id.desc())
        )
        record = IntelligenceRecord(
            record_id=f"event-{event.id}:revision-{revision.id}",
            data_mode="live",
            source_id=spec["id"],
            source_name=spec["name"],
            source_type="official",
            organization_id=spec.get("organization_id", spec["id"]),
            canonical_url=event.canonical_url,
            permitted_method="licensed_text",
            license_name=spec["reuse_policy"]["license"],
            reuse_audit_ref=spec["reuse_policy"]["evidence_ref"],
            original_title=event.title,
            title_zh=payload["title_zh"],
            source_published_at=pub,
            publication_precision="instant" if pub else "unknown",
            fetched_at=datetime.fromisoformat(event.fetched_at),
            last_verified_at=now,
            countries=json.loads(event.countries_json),
            ports=json.loads(event.ports_json),
            primary_domain=domain,
            implementation_priority=PRIORITIES.get(domain),
            event_kind=kind,
            event_lifecycle=event.lifecycle
            if event.lifecycle in ["announced", "active", "resolved", "cancelled"]
            else "unknown",
            content_severity={"高": "high", "中": "medium", "低": "low"}.get(event.risk_level, "unknown"),
            severity_reasons=json.loads(event.risk_reasons_json),
            operational_state="resolved" if event.lifecycle == "resolved" else "unknown",
            evidence_confidence="source_checked",
            business_relevance=rel,
            evidence_snippets=[evidence],
            factual_summary_zh=[
                FactualStatement(
                    text_zh="官方页面原文摘录，须阅读原文核实；未作语义翻译。", evidence_ids=[ev_id]
                )
            ],
            potential_impacts=[
                Inference(
                    text_zh=impacts.get(domain, "目前无足够证据判断业务影响，不调整基础计划。"),
                    evidence_ids=[ev_id],
                )
            ],
            suggested_checks_actions=[
                SuggestedAction(
                    text_zh="核实公告适用日期、后续更新和具体业务关联。",
                    evidence_ids=[ev_id],
                    verification_question="本公告是否仍有效，且适用于相关产品、港口或航次？",
                )
            ],
            applicability=Applicability(
                applicability_note_zh="状态、辖区和电解液适用性须条款级核实；未由日期推导。"
            )
            if domain == "B"
            else None,
            status="excluded" if rel.decision == "excluded" else "analyzed",
            dedup_key=f"live:{event.canonical_url}",
            update_version=session.scalar(
                select(func.count(RawRevision.id)).where(RawRevision.event_id == event.id)
            ),
            previous_record_ref=f"event-{event.id}:revision-{previous.id}" if previous else None,
            quality_flags=flags,
        )
        payload["content_v1"] = record.model_dump(mode="json")
        payload["content_rule_version"] = VERSION
        analysis.payload_json = json.dumps(payload, ensure_ascii=False)
        count += 1
    return count


def collect_content(factory, specs, fetcher=None, now=None):
    fixed_now = now
    now = now or utcnow()
    results = []
    for spec in specs:
        try:
            require_permission(spec, now)
        except (AccessBlocked, ValueError) as exc:
            results.append(
                {
                    "source": spec["id"],
                    "status": "BLOCKED",
                    "failure_stage": "permission",
                    "restriction": str(exc),
                    "writes": {},
                }
            )
            continue
        result = run_collection(factory, [spec], fetcher=fetcher, provider=RuleProvider())[0]
        try:
            with factory.begin() as session:
                result["content_assessments_written"] = attach_content(session, spec, fixed_now or utcnow())
        except Exception as exc:
            result["status"] = "PARTIAL"
            result["failure_stage"] = "content_assessment"
            result["assessment_error"] = type(exc).__name__
        results.append(result)
    return results
