"""Deterministic decision support: evidence, user context, inference and actions remain separate."""

import json
import re
from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select

from scm.platform.contracts import Record
from scm.platform.models import Audit, DecisionCard, Evidence, Item
from scm.platform.service import assess, audit, company_name
from scm.ports.engine import grounded_ports
from scm.ports.registry import registry
from scm.settings import ROOT, utcnow

VERSION = "decision-2026-11-13.1"
STATES = ["pending", "confirmed", "ignored", "in_progress", "resolved"]
PATTERNS = [
    ("ports", "strike", r"\bstrike\b|罢工"),
    ("ports", "shutdown", r"\b(?:port closure|port is closed|halted operations|suspended operations)\b|停工"),
    ("ports", "congestion", r"\bcongestion\b|拥堵"),
    ("ports", "channel_restriction", r"\b(?:channel restriction|navigation restriction)\b|航道限制"),
    ("ports", "terminal_adjustment", r"\bterminal.{0,30}(?:adjust|restrict)|码头作业"),
    ("ports", "service_disruption", r"\b(?:blank sailing|port omission|service disruption)\b|停航"),
    ("capacity", "cancelled", r"\bcancell?ed\b|取消"),
    ("capacity", "delayed", r"\bdelay(?:ed)?\b|延期"),
    (
        "capacity",
        "operating",
        r"\b(?:began production|started production|begins production|commercial production started)\b|正式投产",
    ),
    (
        "capacity",
        "planned_start",
        r"\b(?:plans? to|scheduled to|expected to).{0,45}(?:production|operat)|计划投产",
    ),
    ("capacity", "new_factory", r"\b(?:new factory|new plant|gigafactory)\b|新建工厂"),
    ("capacity", "expansion", r"\bexpan(?:sion|d|ding)\b|扩产"),
    ("capacity", "investment", r"\binvest(?:ment|ing|s)?\b|投资"),
    ("market", "surcharge", r"\bsurcharge\b|附加费"),
    ("market", "route_change", r"\b(?:route change|service rotation|blank sailing)\b|航线变更"),
    ("market", "fuel_price", r"\b(?:diesel|gas oil|fuel price)\b|柴油"),
    ("market", "market_index", r"\b(?:freight index|market index)\b|运价指数"),
    ("market", "freight_rate", r"\bfreight rate\b|运价"),
]


class BusinessLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    link_id: str = Field(min_length=1, max_length=120)
    entity_type: str
    entity_id: str = Field(min_length=1, max_length=200)
    role: str = Field(default="", max_length=200)
    region: str = Field(default="", max_length=100)
    route: str = Field(default="", max_length=200)
    transport: str = Field(default="", max_length=200)
    cargo: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=200)
    country: str = Field(default="", max_length=2)

    @field_validator("country")
    @classmethod
    def country_code(cls, value):
        return Record.countries(value) if value else value

    @model_validator(mode="after")
    def valid(self):
        if self.entity_type not in [
            "port",
            "company",
            "project",
            "route",
            "transport",
            "cost_category",
            "factory",
        ]:
            raise ValueError("Unsupported entity type")
        if self.entity_type == "port" and self.entity_id not in {p.id for p in registry().ports}:
            raise ValueError("Unknown registered port")
        return self


def links(session, mode):
    if mode not in ["live", "demo", "manual"]:
        raise ValueError("Explicit namespace required")
    row = session.scalar(
        select(Audit).where(Audit.source_id == "decision-links", Audit.mode == mode).order_by(Audit.id.desc())
    )
    raw = (
        json.loads(row.payload_json)["links"]
        if row
        else json.loads((ROOT / "config/decision_links.json").read_text(encoding="utf-8"))[mode]
    )
    return [BusinessLink.model_validate(r) for r in raw]


def save_links(session, mode, values, actor, reason):
    if mode not in ["live", "demo", "manual"] or not actor.strip() or not reason.strip():
        raise ValueError("Namespace, reviewer and reason required")
    records = [BusinessLink.model_validate(r) for r in values]
    if len({r.link_id for r in records}) != len(records):
        raise ValueError("Duplicate link ids")
    if any((mode == "demo") != r.link_id.startswith("DEMO-") for r in records):
        raise ValueError("DEMO links must remain in their namespace")
    payload = [r.model_dump() for r in records]
    if payload == [r.model_dump() for r in links(session, mode)]:
        return "unchanged"
    audit(
        session,
        "decision-links",
        mode,
        {"links": payload, "actor": actor, "reason": reason, "origin": "USER_PROVIDED"},
    )
    session.flush()
    return "updated"


def extract(raw, now=None):
    now = now or utcnow()
    text = raw["body"] + "\n" + raw["title"]
    sentences = re.split(r"(?<=[.!?。])\s+|\n", text)
    found = []
    for module, kind, pattern in PATTERNS:
        if raw["module"] != module:
            continue
        quote = next((s for s in sentences if re.search(pattern, s, re.I)), None)
        if quote:
            uncertain = bool(
                re.search(r"\b(?:may|could|possible|rumour|not|no)\b|可能|据传|未确认", quote, re.I)
            )
            found.append({"type": kind, "quote": quote, "hypothesis": uncertain})
    if raw.get("operational_event_id"):
        found = [
            {
                "type": "operational_notice",
                "quote": raw["field_evidence"]["operational_status"],
                "hypothesis": False,
            }
        ]
    if (
        raw["module"] == "capacity"
        and raw.get("project_id")
        and raw.get("field_evidence", {}).get("project_status")
    ):
        found = [
            {
                "type": raw["project_status"],
                "quote": raw["field_evidence"]["project_status"],
                "hypothesis": False,
            }
        ]
    # Plans cannot become an actual operating event because they mention production.
    if any(e["type"] == "operating" for e in found) and re.search(
        r"\b(?:plans? to|expected to|scheduled to)\b", text, re.I
    ):
        found = [e for e in found if e["type"] != "operating"]
    publication = datetime.fromisoformat(raw["published_at"]) if raw.get("published_at") else None
    observation = datetime.fromisoformat(raw["observed_at"]) if raw.get("observed_at") else None
    temporal_anchor = observation or publication
    start = datetime.fromisoformat(raw["effective_at"]) if raw.get("effective_at") else None
    end = datetime.fromisoformat(raw["expires_at"]) if raw.get("expires_at") else None
    validity = "unknown"
    if temporal_anchor and temporal_anchor > now:
        validity = "future_publication"
    elif end and end <= now:
        validity = "expired"
    elif start and start > now:
        validity = "not_yet_effective"
    elif start and end and start <= now < end:
        validity = "active_interval_unconfirmed"
    elif temporal_anchor:
        validity = "historical" if now - temporal_anchor > timedelta(days=30) else "recent_notice_unconfirmed"
    ports = grounded_ports(text, [p.id for p in registry().ports])
    companies = []
    for c in json.loads((ROOT / "config/platform_companies.json").read_text(encoding="utf-8"))["companies"]:
        if any(re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", text, re.I) for a in c["aliases"]):
            companies.append(c["name"])
    if raw["company"] != "unknown":
        companies.append(company_name(raw["company"]))
    if raw["module"] == "capacity":
        facility_context = bool(raw.get("project_id") or raw.get("factory") or companies) or (
            bool(re.search(r"battery|batteries|electrolyte|电池|电解液", text, re.I))
            and bool(re.search(r"factory|plant|manufactur|工厂|生产基地", text, re.I))
        )
        if not facility_context:
            found = []  # Generic investment/policy prose is not an enterprise project.
    return {
        "types": found,
        "validity": validity,
        "ports": ports,
        "companies": sorted(set(companies)),
        "project": raw.get("project_id"),
        "route": raw.get("route"),
        "country": raw["country"],
        "transport": raw.get("transport"),
        "factory": raw.get("factory"),
        "effective_at": raw.get("effective_at"),
        "expires_at": raw.get("expires_at"),
        "status": raw["project_status"] if raw["module"] == "capacity" else "unknown",
        "confidence_basis": "原文模式和显式字段；未经语义/业务核实",
    }


def make_card(session, item, evidence, now=None):
    now = now or utcnow()
    raw = json.loads(evidence.raw_json)
    extraction = extract(raw, now)
    assessment = assess(Record.model_validate(raw), now)
    matches = []
    configured_links = links(session, item.mode)
    for link in configured_links:
        match = (
            (link.entity_type == "port" and link.entity_id in extraction["ports"])
            or (link.entity_type == "company" and company_name(link.entity_id) in extraction["companies"])
            or (
                link.entity_type == "project"
                and link.entity_id == extraction["project"]
                and (not link.company or company_name(link.company) in extraction["companies"])
            )
            or (link.entity_type == "route" and link.entity_id == extraction["route"])
            or (link.entity_type == "transport" and link.entity_id == extraction["transport"])
            or (
                link.entity_type == "factory"
                and link.entity_id == extraction["factory"]
                and (not link.company or company_name(link.company) in extraction["companies"])
            )
            or (
                link.entity_type == "cost_category"
                and link.entity_id == "diesel"
                and any(e["type"] == "fuel_price" for e in extraction["types"])
            )
        )
        # Transport is only associated through explicitly configured context on an entity match.
        if link.country and link.country != raw["country"]:
            match = False
        if match:
            matches.append(link.model_dump())
    # Reuse existing de-identified port profiles; explicit typed links take precedence.
    from scm.ports.detail import profile

    for port_id in extraction["ports"]:
        if any(link.entity_type == "port" and link.entity_id == port_id for link in configured_links):
            continue
        value = profile(session, port_id, item.mode)
        if value.usage.strip() or value.routes.strip():
            matches.append(
                {
                    "entity_type": "port",
                    "entity_id": port_id,
                    "role": value.usage,
                    "route": value.routes,
                    "transport": value.transport,
                    "cargo": value.cargo,
                    "alternatives": value.alternatives,
                    "origin": "USER_PROVIDED_EXISTING_PORT_PROFILE",
                }
            )
    scope_unconfirmed = any(p.id in extraction["ports"] and not p.scope_confirmed for p in registry().ports)
    kinds = {e["type"] for e in extraction["types"]}
    from scm.platform.entities import company_id, operations, projects

    entity = None
    representative = True
    if raw.get("operational_event_id"):
        entity = next(
            (
                e
                for e in operations(session, item.mode, now)
                if e["event_id"] == raw["operational_event_id"] and e["scope"] == raw["event_scope"]
            ),
            None,
        )
        if entity:
            representative = bool(entity["current"] and entity["current"]["evidence_id"] == evidence.id)
            extraction["status"] = entity["state"]
            extraction["validity"] = entity["state"]
    elif raw["module"] == "capacity" and raw.get("project_id"):
        entity = next(
            (
                e
                for e in projects(session, item.mode)
                if e["project_id"] == raw["project_id"] and e["company_id"] == company_id(raw["company"])
            ),
            None,
        )
        if entity:
            representative = entity["current"]["evidence_id"] == evidence.id
    blocked_time = extraction["validity"] in [
        "historical",
        "expired",
        "future_publication",
        "resolved",
        "cancelled",
        "unknown",
    ]
    high_value = (
        bool(kinds)
        and representative
        and not (entity and entity.get("conflicts"))
        and not blocked_time
        and any(not e["hypothesis"] for e in extraction["types"])
        and item.review_status != "rejected"
    )
    if assessment["relevance"] == "excluded" and not kinds:
        high_value = False
    actions = []
    if kinds & {
        "strike",
        "shutdown",
        "congestion",
        "channel_restriction",
        "terminal_adjustment",
        "service_disruption",
        "route_change",
        "operational_notice",
    }:
        actions = [
            "联系货代/承运人核实公告适用航线及运输方式。",
            "若存在相关在途货物，由授权人员检查；系统未连接订单。",
            "如影响获确认，人工评估候选替代港和接收限制。",
        ]
    elif raw["module"] == "capacity" and kinds:
        actions = ["核实项目编号、产品、计划与实际投产状态。", "跟踪后续企业公告；计划产能不得计为已投产。"]
    elif raw["module"] == "market" and kinds:
        actions = [
            "重新向承运人/货代获取适用航线、有效期和费用口径的报价。",
            "关注同币种同单位的后续观测；公共指标不等于合同价格。",
        ]
    else:
        actions = ["当前不构成高价值业务事件；保留背景并继续核实来源覆盖。"]
    if blocked_time:
        actions = ["仅历史/过期/未来背景；核实后续公告，不据此启动当前运营调整。"]
    attest = session.scalar(
        select(Audit)
        .where(Audit.source_id == "decision-facts-" + str(evidence.id), Audit.mode == item.mode)
        .order_by(Audit.id.desc())
    )
    checked_quotes = json.loads(attest.payload_json)["quotes"] if attest else []
    checked = False
    facts = [
        {
            "quote": e["quote"],
            "status": "human_confirmed" if checked else "unverified_source_claim",
            "url": raw["url"],
        }
        for e in extraction["types"]
        if not e["hypothesis"]
    ]
    from scm.platform.models import PlatformSource

    source_spec = json.loads(session.get(PlatformSource, item.source_id).spec_json)
    return {
        "entity_summary": entity,
        "entity_representative": representative,
        "rule_version": VERSION,
        "source_quality": {
            "configured_confidence": source_spec.get("confidence", "unreviewed"),
            "reuse_permission": source_spec.get("reuse_policy", {}).get("permission", "unknown"),
            "provenance": raw["verification"],
            "human_review": item.review_status,
        },
        "item_id": item.id,
        "evidence_id": evidence.id,
        "version": item.version,
        "mode": item.mode,
        "title": raw["title"],
        "source_id": item.source_id,
        "source_url": raw["url"],
        "sha256": evidence.sha256,
        "published_at": raw["published_at"],
        "fetched_at": raw["fetched_at"],
        "observed_at": raw.get("observed_at"),
        "structured_extraction": {
            k: raw.get(k)
            for k in [
                "project_id",
                "factory",
                "project_status",
                "capacity",
                "capacity_unit",
                "capacity_basis",
                "location",
                "product",
                "planned_start",
                "actual_start",
                "operational_event_id",
                "operational_status",
                "event_scope",
                "status_at",
                "investment",
                "value",
                "currency",
                "unit",
                "price_type",
            ]
        },
        "normalization_note": "观测价格单位来自适配器显式换算；原始数值/单位在单元格证据中，非企业合同报价"
        if raw.get("observed_at")
        else "显式字段/规则分类待核实",
        "event": extraction,
        "facts": facts,
        "hypotheses": [e for e in extraction["types"] if e["hypothesis"]],
        "verified_facts": [
            dict(f, status="human_attested_not_independently_validated")
            for f in facts
            if f["quote"] in checked_quotes
        ],
        "review_status": item.review_status,
        "source_reliability": "人工输入待核实" if item.mode == "manual" else "来源可追溯，事实未经独立核验",
        "severity": assessment["risk_level"],
        "severity_reason": assessment["risk_reason"],
        "business_relevance": "matched_user_context" if matches else "unknown",
        "user_context": matches,
        "impact_level": "potential_unconfirmed"
        if matches and high_value and not scope_unconfirmed
        else "unknown",
        "impact": "可能影响已配置的运输安排/供应布局/成本类别，须核实适用性。"
        if matches and high_value and not scope_unconfirmed
        else "影响未知；缺少已核实业务关联或合格当前事件。",
        "missing": ["真实订单/合同报价/适用货物未接入", "事件持续状态和业务适用需人工确认"]
        + ([] if matches else ["未配置或未匹配脱敏业务关联"])
        + (["港口/码头范围映射未确认"] if scope_unconfirmed else []),
        "verification_tasks": [
            "核实原文、发布日期、生效范围及后续更正",
            "人工确认提取和业务关联，不将引文存在当语义核实",
        ],
        "candidate_actions": actions,
        "high_value": high_value,
        "as_of": now.isoformat(),
        "note": "规则推断与候选行动，不是最优方案或损失/延误预测",
    }


def refresh(session, mode, now=None):
    if mode not in ["live", "demo", "manual"]:
        raise ValueError("Namespace required")
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    for item in session.scalars(select(Item).where(Item.mode == mode)):
        ev = session.scalar(
            select(Evidence).where(Evidence.item_id == item.id, Evidence.version == item.version)
        )
        payload = make_card(session, item, ev, now)
        card = session.scalar(select(DecisionCard).where(DecisionCard.evidence_id == ev.id))
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if card is None:
            card = DecisionCard(
                evidence_id=ev.id,
                mode=mode,
                payload_json=encoded,
                created_at=utcnow().isoformat(),
                state="pending",
            )
            session.add(card)
            counts["inserted"] += 1
        else:
            old = json.loads(card.payload_json)
            old.pop("as_of", None)
            comparison = dict(payload)
            comparison.pop("as_of", None)
            if old == comparison:
                counts["unchanged"] += 1
            else:
                card.payload_json = encoded
                counts["updated"] += 1
    session.flush()
    return counts


def cards(session, mode, high_only=False):
    refresh(session, mode)
    result = []
    for card in session.scalars(
        select(DecisionCard).where(DecisionCard.mode == mode).order_by(DecisionCard.id.desc())
    ):
        ev = session.get(Evidence, card.evidence_id)
        item = session.get(Item, ev.item_id)
        if ev.version != item.version:
            continue
        payload = json.loads(card.payload_json)
        if high_only and (not payload["high_value"] or card.state in ["ignored", "resolved"]):
            continue
        result.append({**payload, "card_id": card.id, "handling_state": card.state})
    return result


def handle(session, card_id, mode, state, actor, reason):
    card = session.get(DecisionCard, card_id)
    if not card or card.mode != mode or state not in STATES or not actor.strip() or not reason.strip():
        raise ValueError("Scoped card/state/reviewer/reason required")
    ev = session.get(Evidence, card.evidence_id)
    item = session.get(Item, ev.item_id)
    if ev.version != item.version:
        raise ValueError("Old evidence version: refresh and review current decision")
    audit(
        session,
        "decision-card-" + str(card_id),
        mode,
        {
            "from": card.state,
            "to": state,
            "actor": actor,
            "reason": reason,
            "evidence_id": ev.id,
            "version": ev.version,
        },
    )
    card.state = state


def attest_facts(session, card_id, mode, quotes, actor, reason):
    card = session.get(DecisionCard, card_id)
    if not card or card.mode != mode or not actor.strip() or not reason.strip():
        raise ValueError("Scoped card/reviewer/reason required")
    ev = session.get(Evidence, card.evidence_id)
    item = session.get(Item, ev.item_id)
    if item.version != ev.version:
        raise ValueError("Old version cannot be attested")
    raw = json.loads(ev.raw_json)
    allowed = {e["quote"] for e in extract(raw)["types"] if not e["hypothesis"]}
    if not quotes or set(quotes) - allowed:
        raise ValueError("Only current extracted source quotes can be attested")
    audit(
        session,
        "decision-facts-" + str(ev.id),
        mode,
        {
            "quotes": quotes,
            "actor": actor,
            "reason": reason,
            "meaning": "human attestation; no independent external verification",
        },
    )
    session.flush()
