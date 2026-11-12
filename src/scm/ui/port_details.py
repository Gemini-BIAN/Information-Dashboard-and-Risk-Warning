"""Map → summary → four-tab port details, reusing the existing offline map and risk service."""

from datetime import datetime

import streamlit as st

from scm.ports.detail import detail, save_profile
from scm.ports.registry import registry
from scm.ports.service import read_alert, snapshots
from scm.settings import TIMEZONE
from scm.ui.port_monitor import LABELS, MAP
from scm.ui.presentation import local_time


def label(value):
    return LABELS.get(value, value)


def render(session, factory, mode):
    ports = registry().ports
    by_id = {p.id: p for p in ports}
    pending = st.session_state.pop("port01_pending", None)
    if st.session_state.get("port_detail_selected") not in by_id:
        requested = st.query_params.get("port", "antwerp")
        st.session_state["port_detail_selected"] = requested if requested in by_id else "antwerp"
    if pending in by_id:
        st.session_state["port_detail_selected"] = pending
        st.session_state["port01_choice"] = pending
    elif st.query_params.get("port_view") != "detail" and st.session_state.get("port01_choice") in by_id:
        st.session_state["port_detail_selected"] = st.session_state["port01_choice"]
    selected = st.session_state["port_detail_selected"]
    st.query_params["port"] = selected
    if st.query_params.get("port_view") == "detail":
        render_detail(session, factory, mode, by_id[selected])
        return selected
    st.subheader("港口监测")
    st.caption("12 个业务地点 · 地图入口 · 无数据不等于运营正常")
    query = st.text_input("搜索港口或国家", key="port01_search")
    countries = st.multiselect("国家筛选", sorted({p.country for p in ports}), key="port01_countries")
    visible = [
        p
        for p in ports
        if (not countries or p.country in countries)
        and (not query or query.casefold() in f"{p.business_label} {p.name_zh} {p.country}".casefold())
    ]
    if not visible:
        st.info("没有匹配的港口；清除筛选后查看全部12个地点。")
        return selected
    if selected not in {p.id for p in visible}:
        selected = visible[0].id
    st.session_state["port01_choice"] = selected
    selected = st.selectbox(
        "选择业务港口",
        [p.id for p in visible],
        format_func=lambda id: by_id[id].business_label,
        key="port01_choice",
    )
    st.session_state["port_detail_selected"] = selected
    st.query_params["port"] = selected
    states = snapshots(session, mode)
    left, right = st.columns([1.65, 1])
    with left:
        rows = [
            {
                **p.model_dump(),
                "state": states[p.id]["state"],
                "severity": states[p.id]["severity"],
                "coverage_verified": any(
                    s.get("coverage") == "working_verified" for s in states[p.id]["coverage"]
                ),
                "coverage_label": " / ".join(s["coverage"] for s in states[p.id]["coverage"]) or "none",
            }
            for p in visible
        ]
        click = MAP(ports=rows, key="port01_world_map", default=None)
        if click and click.get("click_id") != st.session_state.get("port01_last_click"):
            st.session_state["port01_last_click"] = click["click_id"]
            if click.get("port_id") in {p.id for p in visible}:
                st.session_state["port01_pending"] = click["port_id"]
                st.rerun()
        st.caption(f"地图显示 {len(visible)}/12 个业务地点；内点为风险，外环为来源覆盖。")
    with right:
        port = by_id[selected]
        snap = states[selected]
        with st.container(border=True):
            st.markdown(f"### {port.business_label} · {port.name_zh}")
            st.caption(port.country)
            st.metric("运营风险", label(snap["severity"]))
            st.write("**当前运营状态：** " + label(snap["state"]))
            st.caption("最近核实：" + local_time(snap["last_check"]))
            st.write(snap["note"])
            if st.button("查看详情", key="port_detail_open", type="primary", use_container_width=True):
                st.query_params["port_view"] = "detail"
                st.rerun()
    return selected


def render_detail(session, factory, mode, port):
    if st.button("← 返回地图", key="port_detail_back"):
        st.query_params["port_view"] = "map"
        st.rerun()
    st.subheader(f"{port.business_label} · {port.name_zh}")
    st.caption(f"{mode.upper()} · 港口详情 · {port.country} · {port.unlocode or 'UN/LOCODE待核实'}")
    data = detail(session, port.id, mode)
    snap = data["snapshot"]
    records = data["records"]
    overview, timeline, evidence, impact = st.tabs(["概览", "公告时间线", "来源证据", "业务影响"])
    with overview:
        cols = st.columns(2)
        cols[0].metric("当前运营状态", label(snap["state"]))
        cols[1].metric("运营风险", label(snap["severity"]))
        st.write(snap["note"])
        st.caption(f"参考位置：{port.latitude}, {port.longitude} · 精度：{port.coordinate_precision}")
        st.info(port.scope_note)
        st.caption(
            f"快照：{local_time(snap['as_of'])} · 最近来源核查：{local_time(snap['last_check'])} · 最近成功：{local_time(snap['last_success'])}"
        )
        st.write("通告业务相关度：" + label(snap["relevance"]))
        st.caption("权限核实：" + local_time(snap.get("last_permission_check")) + "；权限核实不是运营核实。")
        st.markdown("#### 风险原因")
        if not snap["events"]:
            st.info("没有合格当前运营证据；状态未知。")
        for e in snap["events"][:3]:
            st.write(e["assessment"]["severity_reason"])
            st.caption(e["assessment"]["business_reason"])
        st.markdown("#### 最近公告与背景资料")
        latest = [r for r in records if r["latest"]][:3]
        if not latest:
            st.info("暂无可追溯公告。")
        for r in latest:
            st.write(
                r["title"] + " · " + ("当前有效公告" if r["current"] else "历史/待核实/背景，不代表当前运营")
            )
        st.markdown("#### 数据覆盖")
        for src in snap["coverage"]:
            st.write(f"{src['name']} · {src['coverage']} · {src['permission']}")
            st.caption(src["reason"])
            st.link_button("官方入口 · " + src["id"], src["url"])
        if not snap["coverage"]:
            st.info("尚无合格来源覆盖。")
        st.caption(snap["metrics"])
        st.markdown("#### 本港站内预警")
        for a in data["alerts"]:
            st.write(f"#{a.id} · {a.kind} · " + ("已读" if a.read_at else "未读"))
            if not a.read_at and st.button("标为已读", key=f"detail_alert_{a.id}"):
                with factory.begin() as writer:
                    read_alert(writer, a.id, mode)
                st.rerun()
        if not data["alerts"]:
            st.info("暂无本港预警；无预警不代表正常。")
    with timeline:
        st.caption("发生时间未知时不推断；优先明示生效时间，其次发布时间。历史版本不继承新版本的生效日期。")
        kind = st.selectbox(
            "公告类型",
            ["全部"] + sorted({r["category"] for r in records}),
            key=f"detail_kind_{port.id}_{mode}",
        )
        status = st.selectbox(
            "事件状态",
            ["全部", "当前有效", "历史/待核实", "历史版本", "背景资料"],
            key=f"detail_state_{port.id}_{mode}",
        )
        dates = st.date_input("时间范围", value=[], key=f"detail_dates_{port.id}_{mode}")
        chosen = [r for r in records if kind == "全部" or r["category"] == kind]
        chosen = [
            r
            for r in chosen
            if status == "全部"
            or (status == "当前有效" and r["current"])
            or (status == "历史/待核实" and not r["current"])
            or (status == "历史版本" and not r["latest"])
            or (status == "背景资料" and r["background"])
        ]
        if len(dates) == 2:
            chosen = [
                r
                for r in chosen
                if (r["effective"] or r["published"])
                and dates[0]
                <= datetime.fromisoformat(r["effective"] or r["published"]).astimezone(TIMEZONE).date()
                <= dates[1]
            ]
        for r in chosen:
            with st.expander(
                f"{r['title']} · v{r['version']} · " + ("当前有效" if r["current"] else "历史/待核实")
            ):
                st.caption(
                    f"生效：{local_time(r['effective'])} · 公布：{local_time(r['published'])} · 发生：未知"
                )
                st.write(f"{r['state']} · {r['category']} · 证据 {r['id']}")
                st.code(r["body"][:1500], language=None)
                st.link_button("查看公告原文", r["url"])
        if not chosen:
            st.info("暂无符合筛选的公告；不推断当前正常。")
    with evidence:
        st.caption(
            "原始内容指纹与正文SHA256分别展示；指纹可能包含标题/日期或结构化字段，不冒称原始HTTP字节哈希。"
        )
        for r in records:
            with st.expander(f"证据 {r['id']} · {r['title']} · v{r['version']}"):
                st.write("发布机构/保存的来源名：" + r["publisher"])
                st.caption(
                    "第三方转发内容的原发布主体仍需核实。"
                    if r["background"]
                    else "机构名称来自已保存来源配置。"
                )
                st.write("人工审核：" + r["review"])
                st.caption(
                    f"发布：{local_time(r['published'])} · 采集：{local_time(r['fetched'])} · 空间：{r['mode']}"
                )
                st.code(r["body"][:3000], language=None)
                st.caption("原始证据指纹 SHA256：" + r["sha256"])
                st.caption("原文正文 SHA256：" + r["body_sha256"])
                st.link_button("跳转原始来源", r["url"])
                if r["background"]:
                    st.warning("背景/人工资料，不作为当前港口状态证据。")
        if not records:
            st.info("尚无本港可追溯原文证据。")
    with impact:
        st.metric("运营风险（规则）", label(snap["severity"]))
        st.write("公告相关度（规则）：" + label(snap["relevance"]))
        st.info(
            "企业业务影响：未知。脱敏配置是用户声明，不是已核实运输事实，不据此计算影响等级或更改风险规则。"
        )
        p = data["profile"]
        with st.form(f"port_profile_{port.id}_{mode}"):
            st.caption("仅填写脱敏信息；配置仅保存在本地现有审计表，按港口与空间隔离。")
            usage = st.text_input("港口使用情况", p.usage)
            routes = st.text_input("脱敏航线", p.routes)
            transport = st.text_input("运输方式", p.transport)
            cargo = st.text_input("货物类型", p.cargo)
            choices = {x.id: x.business_label for x in registry().ports if x.id != port.id}
            alternatives = st.multiselect(
                "候选替代港口（不代表已可用）",
                list(choices),
                default=p.alternatives,
                format_func=lambda x: choices[x],
            )
            actor = st.text_input("配置人")
            reason = st.text_input("修改原因")
            if st.form_submit_button("保存脱敏配置"):
                try:
                    with factory.begin() as writer:
                        p = save_profile(
                            writer,
                            port.id,
                            mode,
                            dict(
                                usage=usage,
                                routes=routes,
                                transport=transport,
                                cargo=cargo,
                                alternatives=alternatives,
                            ),
                            actor,
                            reason,
                        )
                    st.success("已保存；业务影响仍待核实。")
                except ValueError as exc:
                    st.error(str(exc))
        if not any([p.usage, p.routes, p.transport, p.cargo, p.alternatives]):
            st.caption("尚未配置港口使用情况，保持未知。")
