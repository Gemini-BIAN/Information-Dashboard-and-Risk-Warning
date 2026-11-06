import json
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from html import escape

from sqlalchemy import select

from scm.collectors.coverage import collection_coverage
from scm.database.models import Analysis, Event, Report, Source
from scm.risk.lifecycle import LIFECYCLE_LABELS
from scm.risk.rules import LEVELS
from scm.settings import TIMEZONE, utcnow


def period_bounds(kind, day=None):
    if kind not in ["daily", "weekly"]:
        raise ValueError("kind must be daily or weekly")
    day = day or utcnow().astimezone(TIMEZONE).date()
    start_day = day if kind == "daily" else day - timedelta(days=day.weekday())
    end_day = start_day + timedelta(days=1 if kind == "daily" else 7)
    return (
        datetime.combine(start_day, time.min, TIMEZONE).astimezone(timezone.utc),
        datetime.combine(end_day, time.min, TIMEZONE).astimezone(timezone.utc),
    )


def report_events(session, mode, start, end):
    # Use publication, not collection time; unknown dates are disclosed separately.
    rows = list(
        session.scalars(select(Event).where(Event.data_mode == mode, Event.review_status != "rejected"))
    )
    selected = [
        e
        for e in rows
        if e.published_at and start <= datetime.fromisoformat(e.published_at) < min(end, utcnow())
    ]
    return sorted(selected, key=lambda e: (LEVELS[e.risk_level], e.published_at), reverse=True)


def generate_report(session, kind, mode, day=None):
    if mode not in ["live", "demo"]:
        raise ValueError("mode must be live/demo")
    start, end = period_bounds(kind, day)
    events = report_events(session, mode, start, end)
    coverage = collection_coverage(session, start, end) if mode == "live" else None
    label = "演示数据 / 非真实新闻" if mode == "demo" else "真实来源 / 待人工审核"
    title = (
        "Daily Intelligence Digest｜供应链情报日报"
        if kind == "daily"
        else "Weekly Supply Chain Intelligence Brief｜供应链情报周报"
    )
    parts = [
        f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>{title}</title><style>body{{font:16px system-ui;max-width:1100px;margin:40px auto;line-height:1.7;color:#173047}}article{{border:1px solid #ccd8df;padding:18px;margin:15px 0}}.mode{{background:#fff3cd;padding:12px}}a{{color:#146789}}</style></head><body>',
        f'<h1>{title}</h1><p class="mode">{label}</p>',
        f"<p>统计周期：{start.astimezone(TIMEZONE).isoformat()} 至 {end.astimezone(TIMEZONE).isoformat()}（右开区间）<br>生成时间：{utcnow().astimezone(TIMEZONE).isoformat()}；当前周期可能尚未结束。</p>",
    ]
    parts.append("<h2>今日重点</h2>" if kind == "daily" else "<h2>本周最重要变化（最多5项）</h2>")
    groups = defaultdict(list)
    for event in events:
        groups[event.topic].append(event)
    top = list(groups.values())[:5] if kind == "weekly" else [[e] for e in events[:5]]
    important = [group for group in top if any(LEVELS[e.risk_level] >= 1 for e in group)]
    if coverage is not None:
        parts.append(
            f"<h2>采集覆盖</h2><p>当期配置来源完整日覆盖：{coverage['covered_sources']}/{coverage['configured_sources']}。{escape(coverage['note'])}</p>"
        )
        if not coverage["adequate"]:
            parts.append(
                "<p class='mode'>采集覆盖不足：存在失败、未测或缺少有效当期采集证据，不能判断本期没有重要新增事件；请勿据此推断市场平静或港口正常。</p>"
            )
        for item in coverage["sources"]:
            parts.append(
                f"<p>{escape(item['name'])}：有效日 {len(item['covered_days'])}/{len(item['required_days'])}；最后真实正文成功 {escape(item['last_success_at'] or '无')}；待核实日 {escape(str(item['failures']))}</p>"
            )
    if not important and (coverage is None or coverage["adequate"]):
        parts.append(
            "<p>本期已采集样本中未识别重要新增事件；这不表示外部无风险或完整覆盖。未通过模拟新闻补足数量。</p>"
        )
    for group in top:
        parts.append(
            f"<p>{escape(group[0].title)}（{escape(group[0].risk_level)}；同专题 {len(group)} 条，专题聚类不等于已确认同一事件）</p>"
        )
    for heading, types in [
        ("行业与政策动态", ["行业产能", "关税贸易", "电池法规", "综合动态"]),
        ("物流与港口风险", ["港口运营", "航线调整"]),
    ]:
        parts.append(f"<h2>{heading}</h2>")
        subset = [e for e in events if e.event_type in types]
        if not subset:
            parts.append("<p>本期无已采集、带发布日期的新增记录。</p>")
        for event in subset:
            analysis = session.scalar(
                select(Analysis).where(Analysis.event_id == event.id).order_by(Analysis.id.desc())
            )
            payload = json.loads(analysis.payload_json) if analysis else {}
            parts.append(
                f"<article><h3>{escape(payload.get('title_zh', event.title))}</h3><p>情报信号严重度：{escape(event.risk_level)}（非当前港口风险）｜生命周期：{LIFECYCLE_LABELS.get(event.lifecycle, event.lifecycle)}｜来源可信度：{event.source_confidence}｜规则：{event.rule_version}｜审核：{event.review_status}｜政策状态：{event.policy_status}｜生效：{escape(event.effective_at or '未知/待核实')}｜到期：{escape(event.expiry_at or '未知')}｜废止：{escape(event.repeal_at or '未知')}</p><p>发布时间：{escape(event.published_at or '未知')}；采集：{event.fetched_at}</p><h4>核心事实（原文证据）</h4>"
            )
            parts.append(
                "<h4>政策状态证据与不确定性</h4>"
                + "".join(f"<p>{escape(r)}</p>" for r in json.loads(event.policy_reasons_json))
            )
            for fact in payload.get("facts", []):
                parts.append(
                    f"<p>{escape(fact['text_zh'])}<blockquote>{escape(fact['quote'])}</blockquote></p>"
                )
            parts.append(
                "<h4>风险规则依据</h4>"
                + "".join(f"<p>{escape(r)}</p>" for r in json.loads(event.risk_reasons_json))
            )
            for name, key in [
                ("潜在业务影响（分析推测）", "potential_impacts"),
                ("建议关注指标", "watch_indicators"),
                ("建议核实或采取行动", "suggested_actions"),
            ]:
                parts.append(
                    f"<h4>{name}</h4>" + "".join(f"<p>{escape(t)}</p>" for t in payload.get(key, []))
                )
            source = session.get(Source, event.source_id)
            reuse = json.loads(source.audit_json).get("reuse_policy", {}) if source else {}
            if reuse.get("license") == "CC BY 4.0":
                parts.append(
                    '<p>© European Union — CC BY 4.0。已抽取正文并加入中文规则模板/分析，修改内容不代表欧盟立场。<a href="https://commission.europa.eu/legal-notice_en">复用许可</a></p>'
                )
            parts.append(
                f'<p>分析时间：{escape(analysis.analyzed_at if analysis else "未知")}；{escape(payload.get("quality_note", ""))}</p><a href="{escape(event.canonical_url, quote=True)}">原始来源 {escape(event.source_id)}</a></article>'
            )
    parts.append(
        "<h2>未来1–3个月规划关注</h2><p>以下为条件性规划建议，不是预测：若港口/航线限制持续，复核运输提前期、替代港与安全库存；若关税或电池法规正式适用，复核到岸成本、追溯准备与合规里程碑。无新增证据时不改变基础计划。</p>"
        if kind == "weekly"
        else "<h2>建议关注事项</h2><p>复核公告适用日期、承运人确认及库存覆盖；不得仅凭港口风险断定具体柜号被甩柜。</p>"
    )
    parts.append(
        "<h2>需要持续跟踪与人工核实</h2><p>政策正式状态、生效日期、具体航次关联、公告是否撤回；语义摘要和来源覆盖仍需审核。</p><h2>来源及数据质量说明</h2>"
    )
    sources = (
        list(session.scalars(select(Source).where(Source.method != "fixture"))) if mode == "live" else []
    )
    for source in sources:
        parts.append(
            f"<p>{escape(source.name)}：{source.last_status}；最后检查 {escape(source.last_checked_at or 'NOT TESTED')}</p>"
        )
    unknown = session.scalars(
        select(Event).where(
            Event.data_mode == mode, Event.published_at.is_(None), Event.review_status != "rejected"
        )
    ).all()
    parts.append(
        f"<p>发布日期未知而未计入本期的记录：{len(unknown)}。正文缺失/访问失败不算采集成功。无可靠等待时间数据时不生成拥堵趋势。风险规则不代表模型准确率；LLM不决定分级。</p></body></html>"
    )
    document = "".join(parts)
    row = session.scalar(
        select(Report).where(
            Report.kind == kind,
            Report.period_start == start.isoformat(),
            Report.period_end == end.isoformat(),
            Report.data_mode == mode,
        )
    )
    if row is None:
        row = Report(kind=kind, period_start=start.isoformat(), period_end=end.isoformat(), data_mode=mode)
        session.add(row)
    row.created_at, row.html = utcnow().isoformat(), document
    session.flush()
    return row
