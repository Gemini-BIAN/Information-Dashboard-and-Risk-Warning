import json
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import select

from scm.collectors.coverage import collection_coverage
from scm.collectors.service import load_demo, register_sources, run_collection
from scm.database.models import (
    Analysis,
    CollectionLog,
    Event,
    PortMetric,
    RawRevision,
    Report,
    ReviewLog,
    ShipmentSnapshot,
    Source,
)
from scm.database.session import session_factory
from scm.exports import safe_csv
from scm.intelligence.service import override_port, reassess_events, review
from scm.reports.service import generate_report, period_bounds
from scm.risk.lifecycle import LIFECYCLE_LABELS
from scm.risk.rules import PORT_ALIASES, port_risk
from scm.settings import ROOT, TIMEZONE, utcnow
from scm.shipments.service import import_csv, shipment_risks

st.set_page_config(page_title="供应链智能情报与风险监控", page_icon="🌐", layout="wide")
st.markdown(
    """
    <style>
    .block-container {max-width: 1250px; padding-top: 1.1rem; padding-bottom: 2rem;}
    h1, h2, h3 {color: #17354c;}
    h1 {font-size: clamp(1.6rem, 2.6vw, 2.4rem) !important; line-height: 1.2;}
    .stMetric {background: #f1f5f9; padding: 12px; border-radius: 10px;}
    [data-testid="stSidebar"] {min-width: 250px; max-width: 290px;}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {gap: .5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_factory():
    factory = session_factory()
    with factory.begin() as session:
        register_sources(session)
        reassess_events(session)
    return factory


factory = get_factory()
st.title("ESCIM · 全球供应链情报与风险监控")
st.caption("海外供应链规划 · 来源可追溯 · 中文情报 · 本地测试版")
mode_label = st.sidebar.radio("数据空间", ["真实数据 Live", "演示数据 Demo"])
mode = "demo" if "Demo" in mode_label else "live"
if mode == "demo":
    st.warning("演示空间：所有示例新闻和航次均为虚构，不代表真实港口状态、政策或运输。")
    if st.sidebar.button("加载/刷新演示Fixtures"):
        from scm.settings import ROOT

        with st.spinner("加载演示"):
            load_demo(factory)
            with factory.begin() as session:
                import_csv(
                    session, (ROOT / "fixtures/demo_shipments.csv").read_text(encoding="utf-8"), "demo"
                )
        st.rerun()
else:
    st.info("真实空间：只有成功采集的数据才会显示。空白或未知不代表没有风险。")
page = st.sidebar.radio(
    "工作台", ["Overview", "Intelligence", "Port Monitor", "Shipment Monitor", "Reports", "Sources & System"]
)
st.sidebar.caption("无API模式：中文规则模板 + 原文摘录；LLM可选。默认时区 Asia/Shanghai。")


def event_detail(session, event):
    analysis = session.scalar(
        select(Analysis).where(Analysis.event_id == event.id).order_by(Analysis.id.desc())
    )
    payload = json.loads(analysis.payload_json) if analysis else {}
    with st.expander(f"#{event.id} · {event.risk_level} · {payload.get('title_zh', event.title)}"):
        st.write(
            f"类型：{event.event_type} ｜ 国家：{', '.join(json.loads(event.countries_json)) or '未知'} ｜ 港口：{', '.join(json.loads(event.ports_json)) or '未识别'}"
        )
        st.write(
            f"政策状态：{event.policy_status} ｜ 生效时间：{event.effective_at or '未知/待核实'} ｜ 审核：{event.review_status}"
        )
        st.caption(
            f"来源：{event.source_id} ｜ 发布：{event.published_at or '未知'} ｜ 抓取：{event.fetched_at} ｜ 分析：{analysis.analyzed_at if analysis else '未知'}"
        )
        st.write(
            f"情报严重度：{event.risk_level}（非当前港口风险）｜生命周期：{LIFECYCLE_LABELS.get(event.lifecycle, event.lifecycle)}｜来源可信度：{event.source_confidence}｜规则：{event.rule_version}"
        )
        st.write(
            f"独立政策日期：生效 {event.effective_at or '未知'}；到期 {event.expiry_at or '未知'}；废止 {event.repeal_at or '未知'}"
        )
        for evidence in json.loads(event.policy_reasons_json):
            st.caption(evidence)
        if event.lifecycle == "unknown" or event.rule_version == "legacy":
            st.warning("事件状态未知、矛盾或规则待更新：需人工核实，不作为当前港口中断的自动证据。")
        source = session.get(Source, event.source_id)
        reuse = json.loads(source.audit_json).get("reuse_policy", {}) if source else {}
        if reuse.get("license") == "CC BY 4.0":
            st.caption(
                "© European Union — CC BY 4.0；已抽取正文并加入中文规则模板/分析，修改不代表欧盟立场。"
            )
            st.link_button(
                "欧委会复用许可", "https://commission.europa.eu/legal-notice_en", key=f"license-{event.id}"
            )
        st.link_button("查看原始来源", event.canonical_url)
        st.markdown("**核心事实与原文依据**")
        for fact in payload.get("facts", []):
            st.write(fact["text_zh"])
            st.text(fact["quote"])
        for label, key in [
            ("潜在影响（推测）", "potential_impacts"),
            ("关注指标", "watch_indicators"),
            ("建议行动", "suggested_actions"),
        ]:
            st.markdown(f"**{label}**")
            for value in payload.get(key, []):
                st.write(value)
        st.markdown("**规则分级依据**")
        for value in json.loads(event.risk_reasons_json):
            st.write(value)
        st.caption(payload.get("quality_note", ""))
        if analysis and analysis.error:
            st.warning(f"分析Provider回退：{analysis.error}")
        raw = session.scalar(
            select(RawRevision).where(
                RawRevision.event_id == event.id, RawRevision.content_hash == event.content_hash
            )
        )
        if raw:
            st.download_button(
                "下载原始正文", raw.body, file_name=f"event-{event.id}.txt", key=f"raw-{event.id}"
            )
        with st.form(f"review-{event.id}"):
            action = st.selectbox(
                "审核操作",
                ["confirmed", "rejected", "pending", "note"],
                format_func=lambda x: {
                    "confirmed": "确认",
                    "rejected": "驳回",
                    "pending": "待审核",
                    "note": "仅备注",
                }[x],
            )
            actor = st.text_input("审核人")
            reason = st.text_area("原因/备注（必填）")
            if st.form_submit_button("保存审核记录"):
                try:
                    with factory.begin() as writer:
                        review(writer, event.id, action, actor, reason)
                    st.success("已记录")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))


with factory() as session:
    events = list(
        session.scalars(
            select(Event).where(Event.data_mode == mode).order_by(Event.published_at.desc(), Event.id.desc())
        )
    )
    if mode == "live":
        coverage = collection_coverage(session, *period_bounds("daily"))
        if not coverage["adequate"]:
            st.warning(
                f"今日采集覆盖不足（{coverage['covered_sources']}/{coverage['configured_sources']}个配置来源）；不能据空数据判断没有重要新闻或港口正常。"
            )
    if page == "Overview":
        visible = [e for e in events if e.review_status != "rejected"]
        columns = st.columns(4)
        for col, label, value in zip(
            columns,
            ["情报记录", "高风险规则信号", "待人工审核", "来源失败/部分失败"],
            [
                len(visible),
                sum(e.risk_level == "高" for e in visible),
                sum(e.review_status == "pending" for e in visible),
                session.scalars(select(Source).where(Source.last_status.in_(["BLOCKED", "PARTIAL"])))
                .all()
                .__len__()
                if mode == "live"
                else 0,
            ],
        ):
            col.metric(label, value)
        st.subheader("最新事件")
        if not visible:
            st.info("暂无数据。可在 Sources & System 采集，或切到 Demo 加载明确标记的Fixtures。")
        for event in visible[:10]:
            event_detail(session, event)
    elif page == "Intelligence":
        st.subheader("情报检索与审核")
        cols = st.columns(4)
        period = cols[0].date_input(
            "发布日期范围",
            value=(
                utcnow().astimezone(TIMEZONE).date() - timedelta(days=30),
                utcnow().astimezone(TIMEZONE).date(),
            ),
        )
        country = cols[1].selectbox(
            "国家", ["全部"] + sorted({v for e in events for v in json.loads(e.countries_json)})
        )
        category = cols[2].selectbox("事件类型", ["全部"] + sorted({e.event_type for e in events}))
        risk = cols[3].selectbox("风险等级", ["全部", "高", "中", "低", "未知"])
        include_unknown = st.checkbox("包括发布日期未知", True)
        include_rejected = st.checkbox("包括已驳回", False)
        filtered = []
        for e in events:
            published = (
                datetime.fromisoformat(e.published_at).astimezone(TIMEZONE).date() if e.published_at else None
            )
            if published is None and not include_unknown:
                continue
            if published and len(period) == 2 and not period[0] <= published <= period[1]:
                continue
            if country != "全部" and country not in json.loads(e.countries_json):
                continue
            if category != "全部" and e.event_type != category or risk != "全部" and e.risk_level != risk:
                continue
            if e.review_status == "rejected" and not include_rejected:
                continue
            filtered.append(e)
        st.download_button(
            "导出筛选结果 CSV",
            safe_csv(
                [
                    {
                        "id": e.id,
                        "title": e.title,
                        "source_url": e.canonical_url,
                        "published_at": e.published_at,
                        "risk_level": e.risk_level,
                        "event_type": e.event_type,
                        "review_status": e.review_status,
                        "data_mode": e.data_mode,
                    }
                    for e in filtered
                ]
            ),
            file_name=f"intelligence-{mode}.csv",
            mime="text/csv",
        )
        st.caption(f"匹配 {len(filtered)} 条；每页显示50条。")
        page_number = st.number_input(
            "页码", min_value=1, max_value=max(1, (len(filtered) + 49) // 50), value=1
        )
        for event in filtered[(page_number - 1) * 50 : page_number * 50]:
            event_detail(session, event)
    elif page == "Port Monitor":
        st.subheader("重点港口详情")
        st.caption("每个港口独立详情视图，可通过查询参数 port 保存选择；公告风险不等于实时拥堵。")
        names = list(PORT_ALIASES)
        requested = st.query_params.get("port", names[0])
        port = st.selectbox("选择港口", names, index=names.index(requested) if requested in names else 0)
        st.query_params["port"] = port
        level, reasons, active = port_risk(session, port, mode)
        st.metric(f"{port} · 当前公告风险", level)
        for reason in reasons:
            st.write(reason)
        metrics = list(
            session.scalars(
                select(PortMetric)
                .where(PortMetric.port == port, PortMetric.data_mode == mode)
                .order_by(PortMetric.observed_at)
            )
        )
        # Never use demo metrics as live series or plot unverified synthetic data.
        if mode == "live" and len(metrics) >= 2:
            st.line_chart(
                pd.DataFrame(
                    [{"observed_at": m.observed_at, "waiting_hours": m.waiting_hours} for m in metrics]
                ).set_index("observed_at")
            )
            for url in sorted({m.source_url for m in metrics}):
                st.link_button("时间序列来源", url)
        else:
            st.info("等待时间 / 拥堵趋势：数据暂不可用。未接入可靠真实时间序列。")
        with st.form("port-override"):
            st.markdown("**人工调整（保留规则结果和审计记录）**")
            selected = st.selectbox("调整等级", ["未知", "低", "中", "高"])
            actor = st.text_input("调整人")
            reason = st.text_input("调整原因（必填）")
            hours = st.number_input("有效小时", min_value=1, max_value=168, value=24)
            if st.form_submit_button("保存人工状态"):
                try:
                    with factory.begin() as writer:
                        override_port(
                            writer, port, mode, selected, actor, reason, utcnow() + timedelta(hours=hours)
                        )
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        st.markdown("**港口事件（含历史/未知日期，具体有效性待核实）**")
        matches = [e for e in events if port in json.loads(e.ports_json) and e.review_status != "rejected"]
        if not matches:
            st.info("尚无可用公告；不能解释为港口正常。")
        for event in matches[:30]:
            event_detail(session, event)
    elif page == "Shipment Monitor":
        st.subheader("航次与ETA快照")
        st.caption(
            "时间必须含时区。示例柜号均以 DEMO- 开头；真实导入只留在本地，勿上传敏感数据。ETA风险为快照变化规则，不是预测。"
        )
        st.download_button(
            "下载 CSV 导入模板",
            (ROOT / "fixtures/shipment_template.csv").read_bytes(),
            file_name="shipment_template.csv",
        )
        st.download_button(
            "下载脱敏虚构示例（仅Demo空间导入）",
            (ROOT / "fixtures/demo_shipments.csv").read_bytes(),
            file_name="demo_shipments.csv",
        )
        upload = st.file_uploader("导入 CSV（最大5MB，最多1万行）", type=["csv"])
        if upload and st.button("校验并导入当前数据空间"):
            try:
                with factory.begin() as writer:
                    result = import_csv(writer, upload.getvalue().decode("utf-8-sig"), mode)
                st.success(str(result))
                st.rerun()
            except (ValueError, UnicodeDecodeError) as exc:
                st.error(str(exc))
        risks = shipment_risks(session, mode)
        st.download_button(
            "导出 ETA 风险 CSV",
            safe_csv([{k: v for k, v in row.items() if k != "linked_events"} for row in risks]),
            file_name=f"eta-risk-{mode}.csv",
        )
        for row in risks:
            with st.expander(
                f"{row['container_number']} | {row['vessel']} / {row['voyage']} → {row['pod']} | {row['risk_level']}"
            ):
                st.write(
                    f"ETA: {row['eta']}；快照数 {row['snapshot_count']}；累计变化 {row['baseline_delta_hours']} h"
                )
                for reason in row["reasons"]:
                    st.write(reason)
                for link in row["linked_events"]:
                    st.write(link["association"])
                    st.link_button(link["title"], link["url"])
                snapshots = list(
                    session.scalars(
                        select(ShipmentSnapshot)
                        .where(
                            ShipmentSnapshot.data_mode == mode,
                            ShipmentSnapshot.container_number == row["container_number"],
                            ShipmentSnapshot.vessel == row["vessel"],
                            ShipmentSnapshot.voyage == row["voyage"],
                            ShipmentSnapshot.pod == row["pod"],
                            ShipmentSnapshot.pol == row["pol"],
                        )
                        .order_by(ShipmentSnapshot.updated_at)
                    )
                )
                st.dataframe(
                    [{"Updated At": s.updated_at, "ETA": s.eta, "Status": s.status} for s in snapshots],
                    hide_index=True,
                )
        if not risks:
            st.info("暂无航次快照。")
    elif page == "Reports":
        st.subheader("日报 / 周报与历史记录")
        with st.form("generate-report"):
            kind = st.selectbox(
                "报告类型", ["daily", "weekly"], format_func=lambda x: "日报" if x == "daily" else "周报"
            )
            day = st.date_input("统计日期（周报取该日期所在周）", value=utcnow().astimezone(TIMEZONE).date())
            if st.form_submit_button("生成 HTML 并保存"):
                with factory.begin() as writer:
                    generate_report(writer, kind, mode, day)
                st.rerun()
        reports = list(
            session.scalars(select(Report).where(Report.data_mode == mode).order_by(Report.created_at.desc()))
        )
        if reports:
            selected_id = st.selectbox(
                "历史报告",
                [r.id for r in reports],
                format_func=lambda i: next(
                    f"#{r.id} {r.kind} {r.period_start} ({r.data_mode})" for r in reports if r.id == i
                ),
            )
            report = next(r for r in reports if r.id == selected_id)
            st.download_button(
                "下载 HTML", report.html, file_name=f"{report.kind}-{report.id}-{mode}.html", mime="text/html"
            )
            components.html(report.html, height=950, scrolling=True)
        else:
            st.info("尚未生成报告。")
    else:
        st.subheader("Sources & System")
        sources = list(session.scalars(select(Source)))
        st.dataframe(
            [
                {
                    "来源": s.name,
                    "URL": s.url,
                    "方法": s.method,
                    "状态": s.last_status,
                    "最后验证": s.last_checked_at,
                    "最后真实正文成功": s.last_success_at,
                }
                for s in sources
            ],
            hide_index=True,
        )
        chosen = st.multiselect("本次采集来源（Live）", [s.id for s in sources if s.method != "fixture"])
        if st.button("执行真实公开来源采集", disabled=mode != "live" or not chosen):
            with factory.begin() as writer:
                specs = register_sources(writer)
            with st.spinner("检查 robots 并采集；单一来源失败不影响其他来源"):
                results = run_collection(factory, [s for s in specs if s["id"] in chosen])
            st.json(results)
        st.caption("定时任务请在独立终端运行 scm schedule。Streamlit 本身不启动后台调度。")
        for source in sources:
            if source.method != "fixture":
                with st.expander(source.name + " · 验证详情"):
                    st.json(json.loads(source.audit_json))
        st.markdown("**采集日志（最近100条）**")
        logs = list(session.scalars(select(CollectionLog).order_by(CollectionLog.id.desc()).limit(100)))
        st.dataframe(
            [
                {
                    "来源": log.source_id,
                    "开始": log.started_at,
                    "完成": log.finished_at,
                    "状态": log.status,
                    "正文数": log.collected,
                    "新增": log.inserted,
                    "更新": log.updated,
                    "错误": log.error,
                }
                for log in logs
            ],
            hide_index=True,
        )
        audits = list(
            session.scalars(
                select(ReviewLog).where(ReviewLog.data_mode == mode).order_by(ReviewLog.id.desc()).limit(100)
            )
        )
        st.markdown("**人工审计记录**")
        st.dataframe(
            [
                {
                    "目标": a.target_type + ":" + a.target_id,
                    "审核人": a.actor,
                    "动作": a.action,
                    "原因": a.reason,
                    "时间": a.created_at,
                }
                for a in audits
            ],
            hide_index=True,
        )
        st.warning("本地MVP，无用户认证；审核人字段是自报身份。不可直接公网部署。无付费API是默认运行路径。")
