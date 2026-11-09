"""Module-specific world locator and right-hand port details, no external map assets."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import select

from scm.database.models import PortAlert
from scm.ports.registry import registry
from scm.ports.service import snapshots
from scm.settings import utcnow
from scm.ui.presentation import local_time

MAP = components.declare_component("escim_port_world", path=str(Path(__file__).parent / "port_map"))
LABELS = {
    "unknown": "未知",
    "stale": "已过期",
    "confirmed_disruption": "已确认中断",
    "confirmed_normal": "已确认正常",
    "high": "高",
    "medium": "中",
    "low": "低",
    "relevant": "直接相关",
    "possibly_relevant": "待核实",
    "excluded": "排除",
}


def render(session, factory, mode):
    st.subheader("港口监测")
    st.caption(f"模块 01 · {len(registry().ports)} 个业务地点 · 风险与覆盖分开 · 无预警不等于正常")
    st.caption(
        "时效门槛：最近核查24小时内，且公布24小时内或原文明示有效期覆盖当前。有效期/抓取时间均不自动证明持续运营实况。"
    )
    ports = registry().ports
    now = utcnow()
    states = snapshots(session, mode, now)
    pending = st.session_state.pop("port01_pending", None)
    if pending:
        st.session_state["port01_choice"] = pending
    if "port01_choice" not in st.session_state:
        requested = st.query_params.get("port", "antwerp")
        st.session_state["port01_choice"] = next(
            (p.id for p in ports if requested in [p.id, p.name]), "antwerp"
        )
    query = st.text_input("搜索港口或国家", key="port01_search")
    countries = st.multiselect("国家筛选", sorted({p.country for p in ports}), key="port01_countries")
    visible = [
        p
        for p in ports
        if (not countries or p.country in countries)
        and (not query or query.casefold() in " ".join([p.business_label, p.name_zh, p.country]).casefold())
    ]
    if not visible:
        st.info("没有匹配的港口；清除筛选后查看全部12个地点。")
        return
    if st.session_state["port01_choice"] not in {p.id for p in visible}:
        st.session_state["port01_choice"] = visible[0].id
    by_id = {p.id: p for p in ports}
    selected = st.selectbox(
        "选择业务港口",
        [p.id for p in visible],
        format_func=lambda id: by_id[id].business_label,
        key="port01_choice",
    )
    st.query_params["port"] = selected
    left, right = st.columns([1.65, 1])
    with left:
        rows = []
        for port in visible:
            snap = states[port.id]
            rows.append(
                {
                    **port.model_dump(),
                    "severity": snap["severity"],
                    "state": snap["state"],
                    "coverage_verified": any(
                        s.get("coverage") == "working_verified" for s in snap["coverage"]
                    ),
                    "coverage_label": " / ".join(s["coverage"] for s in snap["coverage"]) or "none",
                }
            )
        click = MAP(ports=rows, key="port01_world_map", default=None)
        if click and click.get("click_id") != st.session_state.get("port01_last_click"):
            st.session_state["port01_last_click"] = click["click_id"]
            if click.get("port_id") in by_id:
                st.session_state["port01_pending"] = click["port_id"]
                st.rerun()
        st.caption(
            f"地图显示 {len(visible)}/{len(ports)} 个业务地点；内点为运营风险，外环为来源覆盖。可放大、平移或用港口选择框操作。"
        )
    snap = states[selected]
    port = by_id[selected]
    with right:
        st.markdown(f"### {port.business_label} · {port.name_zh}")
        st.write(port.country)
        st.metric(f"{port.name} · 运营严重度", LABELS.get(snap["severity"], snap["severity"]))
        st.write("**当前运营状态：** " + LABELS.get(snap["state"], snap["state"]))
        st.write("**业务相关性：** " + LABELS.get(snap["relevance"], snap["relevance"]))
        st.caption(
            f"截至 {snap['as_of']}；最近来源检查 {local_time(snap['last_check'])}；最近成功 {local_time(snap['last_success'])}"
        )
        st.caption(
            "最近权限审计：" + local_time(snap.get("last_permission_check")) + "；权限审计不是运营数据刷新。"
        )
        st.info(port.scope_note)
        st.write(snap["note"])
        st.markdown("**来源覆盖与证据**")
        if not snap["coverage"]:
            st.warning("none：尚无已配置的合格运营来源。")
        for source in snap["coverage"]:
            st.write(f"{source['name']}：{source['coverage']} / {source['permission']}")
            st.caption(source["reason"])
            st.link_button("人工查看官方来源 · " + source["id"], source["url"])
        st.markdown("**船舶动态（预留）**")
        st.caption(snap["metrics"])
        st.markdown("**中文分析与条件建议**")
        st.caption("规则引擎负责风险；可选LLM失败明确降级。不是已核实预测。")
        if not snap["events"]:
            st.write("事实：没有合格当前运营证据。")
        st.write("条件建议：如需要调整计划，先人工核实官方公告、承运人适用航次及危险品/ISO Tank接收条件。")
        st.markdown("**事件历史**")
        st.number_input("历史窗口（天）", min_value=1, max_value=3650, value=30, key="port01_history_days")
        st.caption("默认30天；扩大窗口可查旧公告。抓取时间不替代公布/生效时间。")
        days = st.session_state.get("port01_history_days", 30)
        history_query = st.text_input("搜索历史标题或通告号", key="port01_event_search")
        events = [
            e
            for e in snap["events"]
            if (
                not e["notice"]["published_at"]
                or datetime.fromisoformat(e["notice"]["published_at"]) >= now - timedelta(days=days)
            )
            and (
                not history_query
                or history_query.casefold()
                in (e["notice"]["title"] + " " + e["notice"]["external_id"]).casefold()
            )
        ]
        if not events:
            st.info("暂无符合范围的运营通告；既有HHM营销文章不作为当前运营证据。")
        for item in events:
            n, a, ai = item["notice"], item["assessment"], item["ai"]
            with st.expander(n["external_id"] + " · " + n["title"] + " · " + a["lifecycle"]):
                st.write("公布：" + local_time(n["published_at"]) + "；抓取：" + local_time(n["fetched_at"]))
                st.write("生效：" + local_time(n["valid_from"]) + " 至 " + local_time(n["valid_until"]))
                st.write(
                    "运营严重度："
                    + a["severity"]
                    + "；业务相关性："
                    + a["relevance"]
                    + "；置信度："
                    + a["confidence"]
                )
                st.write(a["severity_reason"])
                st.write(a["business_reason"])
                st.caption(a["uncertainty"])
                st.markdown("**事实与原文证据**")
                for fact in ai["facts"]:
                    st.code(fact["quote"], language=None)
                st.markdown("**中文分析与条件建议（推测）**")
                st.write(ai["summary_zh"])
                st.caption(ai["note"])
                for text in ai["potential_impacts"] + ai["tasks"]:
                    st.write(text)
                st.link_button("通告原始来源", n["url"])
                if item.get("terms_url"):
                    st.link_button("来源许可/条款", item["terms_url"])
    st.markdown("### 站内预警收件箱")
    alerts = list(
        session.scalars(select(PortAlert).where(PortAlert.data_mode == mode).order_by(PortAlert.id.desc()))
    )
    only_unread = st.checkbox("仅未读", value=True, key="port01_unread")
    st.caption(
        f"事件级通知 {len(alerts)} 条，未读 {sum(a.read_at is None for a in alerts)} 条；Teesport/Middlesbrough共享事件不重复通知。"
    )
    for alert in alerts:
        if only_unread and alert.read_at:
            continue
        payload = json.loads(alert.summary_json)
        st.write(
            f"#{alert.id} {alert.kind} · {payload['notice']['title']} · {', '.join(payload['assessment']['ports'])}"
        )
        if not alert.read_at and st.button("标为已读", key="port01_read_" + str(alert.id)):
            from scm.ports.service import read_alert

            with factory.begin() as writer:
                read_alert(writer, alert.id, mode)
            st.rerun()
    if not alerts:
        st.info("暂无站内预警；缺少数据不表示港口正常。")
    if mode == "demo" and st.button("加载模块01虚构演示", key="port01_seed"):
        from scm.ports.demo import seed

        seed(factory)
        st.rerun()
    if st.button("生成港口运营日报", key="port01_daily"):
        from scm.ports.report import daily

        with factory.begin() as writer:
            report = daily(writer, mode)
            st.session_state["port01_digest_" + mode] = report.html
        st.success("已保存至Reports，独立port_daily类型。")
    if st.session_state.get("port01_digest_" + mode):
        st.download_button(
            "下载港口日报HTML",
            st.session_state["port01_digest_" + mode],
            file_name="port01-" + mode + ".html",
            mime="text/html",
        )
    return selected
