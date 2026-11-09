"""Read-only UI semantics. Never changes stored grades, lifecycle or provenance."""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select

from scm.database.models import Analysis
from scm.risk.lifecycle import RULE_VERSION
from scm.risk.rules import LEVELS
from scm.settings import TIMEZONE, utcnow

NAVIGATION = {
    "Overview": "态势总览",
    "Intelligence": "情报研判",
    "Port Monitor": "港口监测",
    "Shipment Monitor": "航次与 ETA",
    "Reports": "情报报告",
    "Sources & System": "来源与系统",
}
REVIEWS = {"pending": "待审核", "confirmed": "人工确认", "rejected": "已驳回"}
STATUS_LABELS = {"PASS": "采集成功", "PARTIAL": "部分失败", "BLOCKED": "受阻", "NOT TESTED": "未验证"}
OPERATIONAL = {"港口运营", "航线调整"}


def decoded(value, default):
    try:
        result = json.loads(value)
        return result if isinstance(result, type(default)) else default
    except (ValueError, TypeError):
        return default


def instant(value):
    try:
        result = datetime.fromisoformat(value)
        return result if result.tzinfo is not None else None
    except (ValueError, TypeError):
        return None


def local_time(value):
    dt = instant(value)
    return dt.astimezone(TIMEZONE).strftime("%Y-%m-%d %H:%M") if dt else "未知"


def freshness(value, now=None):
    dt = instant(value)
    if dt is None:
        return "未取得有效时间"
    age = ((now or utcnow()) - dt).total_seconds() / 3600
    if age < 0:
        return "未来时间 · 待核实"
    if age < 1:
        return "1小时内更新"
    return f"{age:.0f}小时前更新" + (" · 已陈旧" if age > 24 else "")


def within_day(value, now):
    dt = instant(value)
    return dt is not None and now - timedelta(hours=24) <= dt <= now


def current_confirmed(event, now=None):
    """Human-reviewed explicit active port evidence, current rule and fresh 24h dates.

    A self-reported review is not independent authentication or a real-time guarantee.
    Announced/resolved/unknown/legacy/future/stale records never qualify.
    """
    now = now or utcnow()
    signals = decoded(event.port_signals_json, {})
    ports = decoded(event.ports_json, [])
    return bool(
        event.review_status == "confirmed"
        and event.event_type in OPERATIONAL
        and event.lifecycle == "active"
        and event.rule_version == RULE_VERSION
        and within_day(event.published_at, now)
        and within_day(event.fetched_at, now)
        and any(
            port in ports and signal.get("lifecycle") == "active" and signal.get("severity") in ["中", "高"]
            for port, signal in signals.items()
        )
    )


def has_battery_title(event):
    return bool(
        re.search(
            r"\b(?:batter(?:y|ies)|electrolyte|catl|northvolt|samsung sdi|lg energy)\b|电池|电解液|宁德时代",
            event.title,
            re.I,
        )
    )


def relevance(event):
    if event.event_type == "行业产能" and not has_battery_title(event):
        return 1, "产能分类 · 业务相关性待核实"
    if event.event_type in ["电池法规", "行业产能"]:
        return 3, "电池/产能主题（文本）"
    if decoded(event.ports_json, []):
        return 3, "涉及重点港口（文本）"
    if event.event_type in OPERATIONAL | {"关税贸易"}:
        return 2, "物流/贸易主题"
    if any(v in decoded(event.countries_json, []) for v in ["欧盟", "德国", "荷兰", "比利时", "匈牙利"]):
        return 1, "区域关注（文本）"
    return 0, "业务相关性待核实"


@dataclass
class EventView:
    event: object
    payload: dict
    tier: int
    priority: str
    relevance_score: int
    relevance_reason: str
    confirmed_current: bool
    fresh: bool

    @property
    def title(self):
        if self.event.event_type == "行业产能" and not has_battery_title(self.event):
            return "产能/行业主题（相关性待核实）｜" + self.event.title
        return self.payload.get("title_zh") or self.event.title

    @property
    def summary(self):
        impacts = self.payload.get("potential_impacts") or ["业务相关性及影响待核实，先阅读原文再调整计划。"]
        return impacts[0]


def make_view(event, payload=None, now=None):
    now = now or utcnow()
    confirmed = current_confirmed(event, now)
    fresh = within_day(event.published_at, now) and within_day(event.fetched_at, now)
    score, reason = relevance(event)
    pub = instant(event.published_at)
    usable_recent = pub is not None and now - timedelta(days=30) <= pub <= now
    if event.review_status == "rejected":
        tier, priority = 4, "已驳回 · 留档"
    elif confirmed:
        tier, priority = 0, "优先处理 · 已确认运营信号"
    elif (
        fresh
        and event.event_type in OPERATIONAL
        and event.lifecycle in ["active", "announced"]
        and event.rule_version == RULE_VERSION
    ):
        tier, priority = 1, "优先核实 · 未确认当前中断"
    elif usable_recent:
        tier, priority = 2, "规划关注 · 非实时告警"
    else:
        tier, priority = 3, "资料核对 · 时效待核实"
    return EventView(event, payload or {}, tier, priority, score, reason, confirmed, fresh)


def build_views(session, events, mode, now=None):
    views = []
    for event in events:
        if event.data_mode != mode:
            continue
        analysis = session.scalar(
            select(Analysis).where(Analysis.event_id == event.id).order_by(Analysis.id.desc())
        )
        views.append(make_view(event, decoded(analysis.payload_json, {}) if analysis else {}, now))
    return sort_views(views)


def sort_views(views):
    def key(view):
        pub = instant(view.event.published_at)
        return (
            view.tier,
            -view.relevance_score,
            -(pub.timestamp() if pub else 0),
            -LEVELS.get(view.event.risk_level, -1),
            view.event.id,
        )

    return sorted(views, key=key)


def dashboard_counts(views):
    visible = [v for v in views if v.event.review_status != "rejected"]
    return {
        "total": len(visible),
        "current": sum(v.confirmed_current for v in visible),
        "unverified": sum(
            v.event.review_status != "confirmed"
            or v.event.lifecycle == "unknown"
            or (v.event.event_type in OPERATIONAL and not v.confirmed_current)
            for v in visible
        ),
        "high_content": sum(v.event.risk_level == "高" for v in visible),
        "pending": sum(v.event.review_status == "pending" for v in visible),
    }


def filter_views(
    views,
    *,
    query="",
    country="全部",
    category="全部",
    severity="全部",
    review="全部",
    lifecycle="全部",
    period=None,
    include_unknown=True,
    include_rejected=False,
):
    output = []
    query = query.strip().casefold()
    for view in views:
        event = view.event
        if event.review_status == "rejected" and not include_rejected and review != "rejected":
            continue
        if (
            query
            and query
            not in " ".join(
                [view.title, event.title, view.summary, event.source_id, str(event.id), event.canonical_url]
            ).casefold()
        ):
            continue
        if country != "全部" and country not in decoded(event.countries_json, []) + decoded(
            event.ports_json, []
        ):
            continue
        if (
            category != "全部"
            and category != event.event_type
            or severity != "全部"
            and severity != event.risk_level
        ):
            continue
        if (
            review != "全部"
            and review != event.review_status
            or lifecycle != "全部"
            and lifecycle != event.lifecycle
        ):
            continue
        pub = instant(event.published_at)
        if pub is None and not include_unknown:
            continue
        if (
            pub
            and period
            and len(period) == 2
            and not period[0] <= pub.astimezone(TIMEZONE).date() <= period[1]
        ):
            continue
        output.append(view)
    return output


def export_rows(views):
    return [
        {
            "id": v.event.id,
            "title": v.event.title,
            "source_url": v.event.canonical_url,
            "published_at": v.event.published_at,
            "fetched_at": v.event.fetched_at,
            "risk_level": v.event.risk_level,
            "event_type": v.event.event_type,
            "content_severity": v.event.risk_level,
            "lifecycle": v.event.lifecycle,
            "confirmed_current_operational": v.confirmed_current,
            "review_status": v.event.review_status,
            "priority": v.priority,
            "relevance_reason": v.relevance_reason,
            "data_mode": v.event.data_mode,
        }
        for v in views
    ]
