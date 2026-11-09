"""Module-specific world locator and right-hand port details, no external map assets."""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from scm.ports.registry import initial_snapshot, registry
from scm.settings import utcnow

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
    st.caption("模块 01 · 12 个业务地点 · 风险与覆盖分开 · 无预警不等于正常")
    ports = registry().ports
    now = utcnow()
    snapshots = {p.id: initial_snapshot(p, now) for p in ports}
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
            snap = snapshots[port.id]
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
            f"地图显示 {len(visible)}/12 个业务地点；内点为运营风险，外环为来源覆盖。可放大、平移或用港口选择框操作。"
        )
    snap = snapshots[selected]
    port = by_id[selected]
    with right:
        st.markdown(f"### {port.business_label} · {port.name_zh}")
        st.write(port.country)
        st.metric(f"{port.name} · 运营严重度", LABELS.get(snap["severity"], snap["severity"]))
        st.write("**当前运营状态：** " + LABELS.get(snap["state"], snap["state"]))
        st.write("**业务相关性：** " + LABELS.get(snap["relevance"], snap["relevance"]))
        st.caption(
            f"截至 {snap['as_of']}；最近来源检查 {snap['last_check'] or '未验证'}；最近成功 {snap['last_success'] or '无'}"
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
        st.caption("规则降级模式：未连接LLM；不是全文翻译或已核实预测。")
        st.write("事实：没有合格当前运营证据。")
        st.write("条件建议：如需要调整计划，先人工核实官方公告、承运人适用航次及危险品/ISO Tank接收条件。")
        st.markdown("**事件历史**")
        st.number_input("历史窗口（天）", min_value=1, max_value=3650, value=30, key="port01_history_days")
        st.caption("默认30天；扩大窗口可查旧公告。抓取时间不替代公布/生效时间。")
        st.info("暂无符合范围的运营通告；既有HHM营销文章不作为当前运营证据。")
    return selected
