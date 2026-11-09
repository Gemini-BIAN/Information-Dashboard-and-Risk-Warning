import json
from datetime import datetime
from html import escape

from sqlalchemy import select

from scm.database.models import PortAlert, Report
from scm.ports.registry import registry
from scm.ports.service import snapshots
from scm.reports.service import period_bounds
from scm.settings import utcnow


def daily(session, mode, day=None):
    if mode not in ["live", "demo"]:
        raise ValueError("Invalid data namespace")
    start, end = period_bounds("daily", day)
    now = utcnow()
    alerts = list(
        session.scalars(select(PortAlert).where(PortAlert.data_mode == mode).order_by(PortAlert.id))
    )
    latest = {a.signal_id: a for a in alerts if start <= datetime.fromisoformat(a.created_at) < min(end, now)}
    states = snapshots(session, mode, now)
    verified = sum(
        any(c["coverage"] == "working_verified" for c in snap["coverage"]) for snap in states.values()
    )
    labels = {p.id: p.business_label for p in registry().ports}
    parts = [
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>模块01 港口运营日报</title><body><h1>模块01 港口运营日报</h1>',
        f"<p>空间：{escape(mode)}；生成：{now.isoformat()}；通知变更窗口 {start.isoformat()} 至 {end.isoformat()}。</p>",
        f"<p>有效运营源覆盖{verified}/{len(states)}；覆盖不足时不能推断正常；不含AIS、ETA或拥堵数值。规则模板/可选AI分析不代替原文。</p>"
        if mode == "live"
        else "<p>DEMO：全部情报为虚构，绝非实际港口状态。</p>",
    ]
    parts.append(
        "<h2>截至生成时的12地点状态</h2><table><tr><th>地点</th><th>当前运营状态</th><th>运营严重度</th><th>业务相关性</th><th>覆盖</th></tr>"
    )
    for id, snap in states.items():
        parts.append(
            f"<tr><td>{escape(labels[id])}</td><td>{snap['state']}</td><td>{snap['severity']}</td><td>{snap['relevance']}</td><td>{escape(', '.join(c['coverage'] for c in snap['coverage']) or 'none')}</td></tr>"
        )
    parts.append("</table>")
    if not latest:
        parts.append(
            "<p>本期无已核实新增运营通知；覆盖不足，不能推断港口正常。不以历史新闻或模拟数据填充。</p>"
        )
    for alert in latest.values():
        payload = json.loads(alert.summary_json)
        n = payload["notice"]
        a = payload["assessment"]
        ai = payload["ai"]
        parts.append(
            f"<article><h2>{escape(n['title'])}</h2><p>通告身份：{escape(n['external_id'])}；变化：{escape(alert.kind)}；原始公布：{escape(n['published_at'] or '未知')}；生效：{escape(n['valid_from'] or '未知')} 至 {escape(n['valid_until'] or '未知')}；通知记录时生命周期：{escape(a['lifecycle'])}；核查时间：{escape(n['fetched_at'])}</p>"
        )
        parts.append(
            f"<p>范围：{escape(', '.join(labels[id] for id in a['ports']))}（共享事件只计一次）；运营严重度：{a['severity']}；业务相关性：{a['relevance']}；{escape(a['uncertainty'])}</p>"
        )
        parts.append(
            "<h3>事实（原文）</h3>"
            + "".join(f"<blockquote>{escape(f['quote'])}</blockquote>" for f in ai["facts"])
        )
        parts.append(
            "<h3>条件性影响与核实任务（分析推测）</h3>"
            + "".join(f"<p>{escape(x)}</p>" for x in ai["potential_impacts"] + ai["tasks"])
        )
        parts.append(
            f'<p>{escape(ai["note"])}</p><a href="{escape(n["url"], quote=True)}">原始来源</a></article>'
        )
    parts.append("</body></html>")
    html = "".join(parts)
    row = session.scalar(
        select(Report).where(
            Report.kind == "port_daily",
            Report.data_mode == mode,
            Report.period_start == start.isoformat(),
            Report.period_end == end.isoformat(),
        )
    )
    if row is None:
        row = Report(
            kind="port_daily", data_mode=mode, period_start=start.isoformat(), period_end=end.isoformat()
        )
        session.add(row)
    row.html, row.created_at = html, now.isoformat()
    session.flush()
    return row
