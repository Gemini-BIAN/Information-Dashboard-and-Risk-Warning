"""Source-backed operational signals; no numeric delay/ETA inference."""

import re
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scm.ports.registry import registry

LEVELS = {"unknown": -1, "low": 0, "medium": 1, "high": 2}


class Notice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_id: str = Field(min_length=1, max_length=160)
    title: str
    body: str = Field(min_length=1, max_length=200000)
    url: str
    published_at: datetime | None
    fetched_at: datetime
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    data_mode: Literal["live", "demo"] = "live"
    verification_type: Literal["LIVE_HTTP", "INJECTED_TEST_CLIENT", "DEMO"] = "LIVE_HTTP"

    @field_validator("published_at", "fetched_at", "valid_from", "valid_until")
    @classmethod
    def aware(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("Timezone required; no date invention")
        return value

    @model_validator(mode="after")
    def interval(self):
        if self.valid_from and self.valid_until and self.valid_from >= self.valid_until:
            raise ValueError("Invalid effective interval")
        if self.data_mode == "live" and self.external_id.startswith("DEMO-"):
            raise ValueError("Demo identifiers cannot enter Live")
        return self


def grounded_ports(text, permitted):
    result = []
    for p in registry().ports:
        if p.id not in permitted:
            continue
        # Tangier city != an implicitly confirmed Tanger Med terminal.
        aliases = ["Tanger Med"] if p.id == "tangier" else p.aliases
        if any(re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", text, re.I) for a in aliases):
            result.append(p.id)
    if re.search(r"\bRiver Tees\b", text, re.I):
        result += [id for id in ["teesport", "middlesbrough"] if id in permitted and id not in result]
    return result


def assess_notice(notice, permitted_ports, now, prior=None):
    text = notice.title + "\n" + notice.body
    low = text.lower()
    ports = grounded_ports(text, permitted_ports)
    kind, severity, lifecycle = "unknown", "unknown", "unknown"
    reason = "未发现明确运营事件；保留但不作为运营预警。"
    if re.search(
        r"port (?:is |remains )?closed|port closure|closure (?:has been )?lifted|operations (?:are |remain )?suspended",
        low,
    ):
        kind, severity = "closure", "high"
    elif re.search(r"port omission|blank sailing", low):
        kind, severity = "port_omission" if "port omission" in low else "blank_sailing", "medium"
    elif re.search(r"\bstrike\b|industrial action", low):
        kind, severity = "strike", "medium"
    elif re.search(
        r"dangerous goods.{0,50}(?:restrict|not accept)|iso tank.{0,40}(?:restrict|not accept)", low
    ):
        kind, severity = "dangerous_goods_restriction", "medium"
    elif re.search(r"route change|traffic restriction|navigation restriction", low):
        kind, severity = "route_change", "medium"
    elif re.search(
        r"operations (?:are )?normal|port (?:is )?open with no restrictions", low
    ) and not re.search(r"not (?:currently )?normal|not open|no longer normal", low):
        kind, severity = "status_normal", "low"
    if (
        re.search(r"no port closure|not (?:currently )?closed|no strike|no disruption|will not strike", low)
        and kind != "status_normal"
    ):
        kind, severity = "unknown", "unknown"
    if kind != "unknown":
        reason = "仅按通告原文识别运营类型与严重度；不推导具体柜号/船期延误。"
        if re.search(
            r"strike (?:has )?ended|operations (?:have )?resumed|closure (?:has been )?lifted|\bcancelled\b|\bcanceled\b|\bwithdrawn\b",
            low,
        ):
            lifecycle = "resolved"
        elif (notice.valid_from and notice.valid_from > now) or re.search(
            r"\bplanned\b|\bscheduled\b|\bwill\b|proposed", low
        ):
            lifecycle = "planned"
        elif re.search(
            r"port (?:is |remains )closed|operations (?:are |remain )suspended|strike is ongoing|restriction is in force|operations (?:are )?normal|port (?:is )?open with no restrictions",
            low,
        ):
            lifecycle = "active"
    if re.search(r"\bcancelled\b|\bcanceled\b|\bwithdrawn\b", low) and prior:
        lifecycle = "resolved"
        if kind == "unknown":
            kind = prior["kind"]
            severity = prior["severity"]
        if not ports:
            ports = [p for p in prior["ports"] if p in permitted_ports]
    if not ports:
        severity = "unknown"
        reason = "没有来源范围内的明确地点匹配；不得用London、Tanger或邻近地点猜测具体港口。"
    if re.search(r"electrolyte|iso[ -]?tank", low):
        relevance = "high"
        business_reason = "原文明示电解液/ISO Tank；具体产品与业务适用性仍待核实。"
    elif re.search(r"dangerous goods|\bimdg\b|\badr\b", low):
        relevance = "medium"
        business_reason = "原文明示危险品运输，但未证明具体电解液/罐箱适用。"
    elif kind != "unknown" and ports:
        relevance = "low"
        business_reason = "一般港航运营关联，未确认危险品或电解液专属影响。"
    else:
        relevance = "unknown"
        business_reason = "业务适用性未知。"
    stale = (
        not notice.published_at
        or notice.published_at > now
        or notice.fetched_at > now
        or now - notice.fetched_at > timedelta(hours=24)
    )
    interval_current = bool(
        notice.valid_from and notice.valid_until and notice.valid_from <= now < notice.valid_until
    )
    if notice.published_at and now - notice.published_at > timedelta(hours=24) and not interval_current:
        stale = True
    if notice.valid_until and notice.valid_until <= now:
        stale = True
    if notice.valid_from and notice.valid_from > now:
        interval_current = False
    current_evidence = bool(
        ports and not stale and lifecycle == "active" and notice.verification_type == "LIVE_HTTP"
    )
    state = "unknown"
    if stale and kind != "unknown":
        state = "stale"
    elif current_evidence and kind == "status_normal":
        state = "confirmed_normal"
    elif current_evidence and kind not in ["unknown", "status_normal"]:
        state = "confirmed_disruption"
    if lifecycle == "resolved":
        state = "unknown"  # resolving one notice does not establish normality of the port
    return {
        "ports": ports,
        "kind": kind,
        "severity": severity,
        "lifecycle": lifecycle,
        "relevance": relevance,
        "severity_reason": reason,
        "business_reason": business_reason,
        "state": state,
        "confidence": "source_checked_not_human_signed"
        if notice.verification_type == "LIVE_HTTP"
        else "demo_or_test_unverified",
        "horizon": "公告有效期内" if notice.valid_until else "当前/未来范围待核实",
        "uncertainty": "运营范围、解除/替代公告及实际承运人服务需人工复核；不推导ETA或延误数值。",
    }
