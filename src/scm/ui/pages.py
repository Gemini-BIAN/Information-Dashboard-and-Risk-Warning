"""Page composition using existing services; no schema or collection-rule changes."""

import inspect
from datetime import timedelta
from html import escape

import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import select

from scm.collectors.service import register_sources, run_collection
from scm.database.models import CollectionLog, PortMetric, Report, ReviewLog, ShipmentSnapshot
from scm.exports import safe_csv
from scm.intelligence.service import override_port
from scm.reports.service import generate_report
from scm.risk.rules import PORT_ALIASES, port_risk
from scm.settings import ROOT, TIMEZONE, utcnow
from scm.shipments.service import import_csv, shipment_risks
from scm.ui.components import card, empty, pill, queue
from scm.ui.presentation import STATUS_LABELS, decoded, freshness, local_time


def overview(session, views, factory, mode, counts):
    c = st.columns(4)
    c[0].metric(
        "当前已确认运营中断",
        counts["current"],
        help="必须24小时内发布/抓取、最新规则、明确active港口证据并人工确认；宣布、未知、历史或单纯高严重度均不计入。Demo仅演示。",
    )
    c[1].metric(
        "未核实 / 状态未知",
        counts["unverified"],
        help="包括尚未人工确认、生命周期未知或不能证明当前有效的运营信号，不代表已发生中断。",
    )
    c[2].metric(
        "高严重度内容",
        counts["high_content"],
        help="原文规则严重度，与当前运营是否中断独立，可与未核实/待审重叠。",
    )
    c[3].metric("待人工审核", counts["pending"], help="待审核的内容，需要核对事实、适用范围及下一步。")
    st.caption(
        f"当前空间共 {counts['total']} 条情报 · 指标可重叠；内容高严重度 ≠ 当前运营中断 ≠ 航次 ETA 风险。"
    )
    st.subheader("例外与待核实队列")
    if counts["current"] == 0:
        st.caption("尚无满足当前确认条件的运营中断；这不是“港口正常”或“供应链安全”的结论。")
    if not views:
        empty(
            "尚未建立可处理的情报队列",
            "先查看来源状态和采集覆盖；可切换Demo检查流程，不能用演示数据填充Live。",
        )
        return
    queue(session, views, factory, mode, "Overview")


def intelligence(session, views, factory, mode):
    st.subheader("情报研判与审核")
    st.caption("主题/港口相关性是文本匹配，不代表实际资产或航次已受影响。所有分析均可回到原文证据。")
    queue(session, views, factory, mode, "Intelligence")


def legacy_ports(session, views, factory, mode):
    st.subheader("港口监测")
    st.caption("公告规则提示、人工风险调整与已确认运营实况分别保留；没有等待时间数据，不绘制模拟实时趋势。")
    names = list(PORT_ALIASES)
    requested = st.query_params.get("port", names[0])
    port = st.selectbox("选择港口", names, index=names.index(requested) if requested in names else 0)
    st.query_params["port"] = port
    level, reasons, _ = port_risk(session, port, mode)
    matches = [
        v for v in views if port in decoded(v.event.ports_json, []) and v.event.review_status != "rejected"
    ]
    c = st.columns(3)
    c[0].metric(
        port + " · 公告规则提示",
        level,
        help="保留原风险规则及人工覆盖，不是实时运行状态；不等同总览中24h已确认中断。",
    )
    c[1].metric("24h已确认运营信号", sum(v.confirmed_current for v in matches))
    c[2].metric("相关公告", len(matches))
    latest = max((v.event.fetched_at for v in matches if v.event.fetched_at), default=None)
    st.caption("公告更新：" + freshness(latest) + " · 最后抓取 " + local_time(latest) + "（Asia/Shanghai）")
    st.info(
        "等待时间 / 拥堵趋势：数据暂不可用。未接入可靠真实时间序列。"
        if not list(
            session.scalars(
                select(PortMetric).where(PortMetric.port == port, PortMetric.data_mode == mode)
            ).all()
        )
        else "时间序列仅使用当前空间已保存的指标，不能推断具体柜号被甩柜。"
    )
    metrics = list(
        session.scalars(
            select(PortMetric)
            .where(PortMetric.port == port, PortMetric.data_mode == mode)
            .order_by(PortMetric.observed_at)
        )
    )
    if mode == "live" and len(metrics) >= 2:
        import pandas as pd

        st.line_chart(
            pd.DataFrame(
                [{"观测时间": m.observed_at, "等待小时": m.waiting_hours} for m in metrics]
            ).set_index("观测时间")
        )
        for url in sorted({m.source_url for m in metrics}):
            st.link_button("时间序列来源", url)
    elif metrics:
        st.caption("不足两个真实观测点，或处于演示空间，不展示拥堵趋势。")
    with st.expander("规则依据与不确定性"):
        for reason in reasons:
            st.write(reason)
    with st.expander("人工调整风险 · 保留审计"):
        with st.form("port-override"):
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
                    st.session_state["scm_flash"] = "人工风险调整已保存；不将其视作运营中断证据"
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    if not matches:
        empty("暂无该港口的可用公告", "不能将缺少公告解释为港口正常；请先核对来源覆盖。")
    for view in matches[:20]:
        card(session, view, factory)


def import_upload(factory, content, mode):
    """Server is capped at 5 MiB; application retains its stricter 5,000,000-byte cap."""
    if len(content) > 5_000_000:
        raise ValueError("文件超过应用5MB上限（5,000,000字节），请拆分后导入。")
    text = content.decode("utf-8-sig")
    with factory.begin() as writer:
        return import_csv(writer, text, mode)


def shipments(session, factory, mode):
    st.subheader("航次与 ETA 风险")
    st.caption("ETA分级只根据快照变化：+24h中、+72h高；不是港口风险、延误预测或甩柜证明。")
    risks = shipment_risks(session, mode)
    c = st.columns(3)
    c[0].metric("已保存航段", len(risks))
    c[1].metric("ETA变化高风险", sum(r["risk_level"] == "高" for r in risks))
    c[2].metric("缺少对比快照", sum(r["snapshot_count"] < 2 for r in risks))
    c = st.columns(2)
    c[0].download_button(
        "下载 CSV 导入模板",
        (ROOT / "fixtures/shipment_template.csv").read_bytes(),
        file_name="shipment_template.csv",
    )
    c[1].download_button(
        "下载脱敏虚构示例（仅Demo空间导入）",
        (ROOT / "fixtures/demo_shipments.csv").read_bytes(),
        file_name="demo_shipments.csv",
    )
    with st.expander("CSV导入 · 最大5MB / 1万行", expanded=not risks):
        st.caption(
            "时间需含时区；只导入已获授权的本地数据，不上传敏感数据到公开仓库或模型。Demo示例不能进入Live。"
        )
        per_file = (
            {"max_upload_size": 5}
            if "max_upload_size" in inspect.signature(st.file_uploader).parameters
            else {}
        )
        upload = st.file_uploader(
            "导入 CSV（最大5MB，最多1万行）", type=["csv"], key=f"{mode}:shipment_csv", **per_file
        )
        if upload and st.button("校验并导入当前数据空间"):
            try:
                result = import_upload(factory, upload.getvalue(), mode)
                st.session_state["scm_flash"] = (
                    f"CSV导入完成：新增 {result['inserted']}，重复跳过 {result['unchanged']}（{mode}）"
                )
                st.rerun()
            except (ValueError, UnicodeDecodeError) as exc:
                st.error(str(exc))
    st.download_button(
        "导出 ETA 风险 CSV",
        safe_csv([{k: v for k, v in row.items() if k != "linked_events"} for row in risks]),
        file_name=f"eta-risk-{mode}.csv",
    )
    for row in risks:
        severity_color = "red" if row["risk_level"] == "高" else "amber" if row["risk_level"] == "中" else ""
        st.markdown(
            pill("ETA规则风险：" + row["risk_level"], severity_color)
            + f' <span class="scm-meta">最后快照 {local_time(row["updated_at"])} · {freshness(row["updated_at"])}</span>',
            unsafe_allow_html=True,
        )
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
                [{"更新时间": s.updated_at, "ETA": s.eta, "状态（原始）": s.status} for s in snapshots],
                hide_index=True,
            )
    if not risks:
        empty("暂无可计算的航次快照", "上传授权CSV后保留每次更新；没有快照不能判断运输正常或具体柜号被甩柜。")


def reports(session, factory, mode):
    st.subheader("情报报告")
    st.caption("日报 / 周报按原始发布日期统计；覆盖不足单列说明，不以空数据推断无新闻。")
    with st.expander("生成报告", expanded=False):
        with st.form("generate-report"):
            kind = st.selectbox(
                "报告类型", ["daily", "weekly"], format_func=lambda v: "日报" if v == "daily" else "周报"
            )
            day = st.date_input("统计日期（周报取该日期所在周）", value=utcnow().astimezone(TIMEZONE).date())
            if st.form_submit_button("生成 HTML 并保存"):
                with factory.begin() as writer:
                    generate_report(writer, kind, mode, day)
                st.session_state["scm_flash"] = "报告已按原发布日期生成，未补造新闻"
                st.rerun()
    rows = list(
        session.scalars(select(Report).where(Report.data_mode == mode).order_by(Report.created_at.desc()))
    )
    if not rows:
        empty("尚无该空间报告", "选择日期生成HTML报告；Live与Demo的报告历史始终隔离。")
        return
    selected_id = st.selectbox(
        "历史报告",
        [r.id for r in rows],
        format_func=lambda i: next(
            f"#{r.id} {'日报' if r.kind == 'daily' else '周报'} · {local_time(r.period_start)} · {r.data_mode}"
            for r in rows
            if r.id == i
        ),
    )
    report = next(r for r in rows if r.id == selected_id)
    c = st.columns([3, 1])
    c[0].caption(
        f"生成于 {local_time(report.created_at)}（Asia/Shanghai） · {freshness(report.created_at)} · {'演示报告，非真实新闻' if mode == 'demo' else '真实来源，仍需审核覆盖与适用范围'}"
    )
    c[1].download_button(
        "下载 HTML", report.html, file_name=f"{report.kind}-{report.id}-{mode}.html", mime="text/html"
    )
    components.html(report.html, height=800, scrolling=True)


def sources(session, factory, mode, source_rows, coverage):
    st.subheader("来源与系统")
    st.caption("成功仅表示当前抓取样本可用，不代表全站覆盖、法律适用或实时港口运行。")
    rows = [s for s in source_rows if s.method != "fixture"]
    c = st.columns(3)
    c[0].metric("今日有效日覆盖", f"{coverage['covered_sources']} / {coverage['configured_sources']}")
    c[1].metric("受阻 / 部分失败", sum(s.last_status in ["BLOCKED", "PARTIAL"] for s in rows))
    c[2].metric("尚未验证", sum(s.last_status == "NOT TESTED" for s in rows))
    st.caption("来源状态是Live采集状态；Demo数据不计入真实覆盖。")
    for source in rows:
        audit = decoded(source.audit_json, {})
        status = STATUS_LABELS.get(source.last_status, source.last_status)
        color = (
            "teal"
            if source.last_status == "PASS"
            else "amber"
            if source.last_status in ["BLOCKED", "PARTIAL"]
            else ""
        )
        with st.container(border=True):
            st.markdown(
                pill(status, color)
                + pill("启用" if source.enabled else "停用")
                + f" <strong>{escape(source.name)}</strong>",
                unsafe_allow_html=True,
            )
            st.caption(
                f"最近检查 {local_time(source.last_checked_at)} · 最近正文成功 {local_time(source.last_success_at)} · {freshness(source.last_success_at)}"
            )
            st.link_button("官方入口", source.url, key=f"entry-{source.id}")
            if audit.get("restriction"):
                st.write(audit["restriction"])
            with st.expander(source.name + " · 验证详情"):
                st.json(audit)
    with st.expander("手动采集与调度"):
        chosen = st.multiselect("本次采集来源（Live）", [s.id for s in rows if s.enabled])
        if st.button("执行真实公开来源采集", disabled=mode != "live" or not chosen):
            with factory.begin() as writer:
                specs = register_sources(writer)
            with st.spinner("检查robots并采集；不绕过许可/访问限制"):
                result = run_collection(factory, [s for s in specs if s["id"] in chosen])
            st.json(result)
        st.caption("独立终端运行 scm schedule；页面不会自动启动调度或触发采集。")
    with st.expander("采集日志 / 错误记录（最近100条）"):
        logs = list(session.scalars(select(CollectionLog).order_by(CollectionLog.id.desc()).limit(100)))
        st.dataframe(
            [
                {
                    "来源": log.source_id,
                    "开始": local_time(log.started_at),
                    "状态": STATUS_LABELS.get(log.status, log.status),
                    "正文数": log.collected,
                    "新增": log.inserted,
                    "更新": log.updated,
                    "错误": log.error,
                }
                for log in logs
            ],
            hide_index=True,
        )
    with st.expander("人工审计记录（当前数据空间）"):
        audits = list(
            session.scalars(
                select(ReviewLog).where(ReviewLog.data_mode == mode).order_by(ReviewLog.id.desc()).limit(100)
            )
        )
        st.dataframe(
            [
                {
                    "目标": a.target_type + ":" + a.target_id,
                    "审核人": a.actor,
                    "动作": a.action,
                    "原因": a.reason,
                    "时间": local_time(a.created_at),
                }
                for a in audits
            ],
            hide_index=True,
        )
    st.caption("本地单用户测试版，审核人为自报身份；没有企业登录/RBAC，不直接公网部署。")


def ports(session, views, factory, mode):
    from scm.ui.port_monitor import render

    render(session, factory, mode)
    with st.expander("既有三港口公告/人工调整（独立历史工具，非当前运营证据）"):
        legacy_ports(session, views, factory, mode)
