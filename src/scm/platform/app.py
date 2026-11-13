"""Unified local platform; existing Module01 renderer remains authoritative."""

import csv
import io
import json
import os
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import select

from scm.database.models import PortAlert
from scm.database.session import session_factory
from scm.platform.adapters import collect, import_file
from scm.platform.demo import seed
from scm.platform.models import Alert, Audit, Evidence, Item, PlatformSource, Report
from scm.platform.service import generate_report, register, review, rows, set_alert, specs
from scm.settings import ROOT
from scm.ui.decision import render as render_decisions
from scm.ui.port_details import render as render_ports

st.set_page_config(page_title="ESCIM 海外供应链情报平台", layout="wide")
st.markdown(
    """<style>.block-container{max-width:1440px} [data-testid="stMetric"]{border:1px solid #dce4ed;border-radius:8px;padding:12px}@media(max-width:600px){.block-container{padding:1rem!important}h1{font-size:1.6rem!important}iframe{max-width:100%}}</style>""",
    unsafe_allow_html=True,
)


@st.cache_resource
def db(url):
    factory = session_factory(url)
    with factory.begin() as session:
        register(session)
    return factory


factory = db(os.getenv("SCM_PLATFORM_DATABASE_URL", "sqlite:///runtime/platform/platform.db"))
mode = st.sidebar.radio(
    "数据空间",
    ["live", "demo", "manual"],
    format_func=lambda x: {
        "live": "LIVE · 官方真实采集",
        "demo": "DEMO · 合成测试数据",
        "manual": "MANUAL · 人工输入待核实",
    }[x],
    key="platform_mode",
)

page = st.sidebar.radio(
    "工作台",
    [
        "统一情报中心",
        "01 港口与物流",
        "02 海外产能与竞争",
        "03 物流市场与成本",
        "日报与周报",
        "预警收件箱",
        "Sources 数据源",
    ],
    key="platform_page",
    index=1 if st.query_params.get("port_view") in ["map", "detail"] else 0,
)
previous_page = st.session_state.get("platform_previous_page")
if page == "01 港口与物流" and previous_page not in [None, "01 港口与物流"]:
    st.query_params["port_view"] = "map"
    st.session_state["port_world_view"] = None
st.session_state["platform_previous_page"] = page
if page == "01 港口与物流" and st.query_params.get("port_view") != "detail":
    st.markdown(
        "<style>.block-container{max-width:none!important;padding:3.5rem 0 0!important}header[data-testid=stHeader]{background:transparent}iframe{display:block;border:0}</style>",
        unsafe_allow_html=True,
    )
else:
    st.title("ESCIM 海外供应链情报平台")
    st.caption(
        {
            "live": "LIVE：官方原文证据，采集成功不代表事实已人工核实或当前运营正常。",
            "demo": "DEMO：所有示例企业、项目与价格均为虚构，禁止用于实际业务决策。",
            "manual": "MANUAL：用户导入，未验证真实性，不进入Live报告。",
        }[mode]
    )
if mode == "demo" and st.sidebar.button("加载 DEMO 合成数据"):
    seed(factory)
    st.rerun()
st.sidebar.caption("默认本地 · 无外部消息推送 · 无LLM · 原始证据与分析分开")


def list_items(module=None):
    with factory() as session:
        all_rows = rows(session, mode, module)
    selected_topic = st.selectbox(
        "主题/模块", ["全部", "ports", "capacity", "market"], key="topic_" + str(module)
    )
    query = st.text_input("搜索标题、原文或企业", key="search_" + str(module))
    country = st.selectbox(
        "国家/地区", ["全部"] + sorted({r["raw"]["country"] for r in all_rows}), key="country_" + str(module)
    )
    company = st.selectbox(
        "企业筛选", ["全部"] + sorted({r["raw"]["company"] for r in all_rows}), key="company_" + str(module)
    )
    risk = st.selectbox("风险等级", ["全部", "unknown", "medium"], key="risk_" + str(module))
    status = st.selectbox(
        "审核状态", ["全部", "pending", "confirmed", "rejected"], key="review_" + str(module)
    )
    dates = st.date_input("发布日期范围（可选）", value=[], key="dates_" + str(module))
    with factory() as session:
        data = rows(
            session,
            mode,
            module,
            query,
            country if country != "全部" else None,
            risk if risk != "全部" else None,
            company if company != "全部" else None,
        )
    data = [
        r
        for r in data
        if (status == "全部" or r["review_status"] == status)
        and (selected_topic == "全部" or r["raw"]["module"] == selected_topic)
    ]
    if len(dates) == 2:
        data = [
            r
            for r in data
            if r["raw"]["published_at"]
            and dates[0] <= datetime.fromisoformat(r["raw"]["published_at"]).date() <= dates[1]
        ]
    st.write(f"匹配情报 {len(data)} 条")
    if not data:
        st.info("暂无匹配情报；覆盖不足不代表无风险。")
    export = io.StringIO()
    writer = csv.writer(export)
    writer.writerow(["mode", "title", "published_at", "source", "risk", "status", "url"])

    def cell(value):
        value = str(value or "")
        return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value

    for r in data:
        raw, a = r["raw"], r["analysis"]
        writer.writerow(
            [
                cell(v)
                for v in [
                    mode,
                    raw["title"],
                    raw["published_at"],
                    r["source_id"],
                    a["risk_level"],
                    r["review_status"],
                    raw["url"],
                ]
            ]
        )
        with st.expander(f"{raw['title']} · {a['risk_level']} · {r['review_status']}"):
            st.write(
                f"模块 {raw['module']} · 数据状态 {raw['data_status']} · 企业 {raw['company']} · {raw['country']}"
            )
            st.caption(
                f"发布 {raw['published_at'] or '未知'} · 采集 {raw['fetched_at']} · 更新 {r['updated_at']} · 版本 {r['version']} · {raw['verification']}"
            )
            if raw.get("observed_at"):
                st.caption("观测日期：" + raw["observed_at"] + "（日精度，UTC午夜约定；非发布日期）")
            st.write("来源可信度：" + r["source_confidence"] + "；配置审查不等于事实人工确认。")
            st.code(raw["body"], language=None)
            st.caption("SHA256（标准化原文及业务字段，不含抓取时间）：" + r["sha256"])
            st.write(a["risk_reason"])
            st.write("业务相关性：" + a["relevance"] + " · " + "; ".join(a["business_reasons"]))
            st.write("潜在影响（推测）：" + a["impact"])
            st.write("建议核实：" + a["action"])
            st.write("质量标志：" + ", ".join(a["quality_flags"]))
            st.link_button("查看原始来源", raw["url"])
            if module == "capacity":
                st.json(
                    {
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
                            "actual_start",
                            "investment",
                            "currency",
                            "planned_start",
                        ]
                    }
                )
                st.caption("公告与导入字段仍待核实；计划产能不计入实际产能；不自动汇总不同项目单位。")
                if raw.get("project_id"):
                    with factory() as session:
                        history = [
                            x
                            for x in rows(session, mode, "capacity")
                            if x["raw"].get("project_id") == raw["project_id"]
                            and x["raw"]["company"] == raw["company"]
                        ]
                    from scm.platform.entities import company_id, projects

                    with factory() as session:
                        entity = next(
                            (
                                p
                                for p in projects(session, mode)
                                if p["project_id"] == raw["project_id"]
                                and p["company_id"] == company_id(raw["company"])
                            ),
                            None,
                        )
                    if entity:
                        st.json(entity)
                    st.markdown("**项目时间线（明确项目编号关联）**")
                    st.dataframe(
                        [
                            {
                                "发布时间": x["raw"]["published_at"],
                                "状态": x["raw"]["project_status"],
                                "证据": x["raw"]["url"],
                            }
                            for x in reversed(history)
                        ],
                        hide_index=True,
                    )
            if module == "market":
                st.json({k: raw[k] for k in ["route", "price_type", "value", "currency", "unit"]})
                st.caption("价格、指数、公告、人工输入和模型估计分别标识；未接入实时价格API。")
            with factory() as session:
                versions = list(
                    session.scalars(
                        select(Evidence).where(Evidence.item_id == r["id"]).order_by(Evidence.version)
                    )
                )
            st.markdown("**证据版本历史**")
            st.dataframe(
                [
                    {
                        "版本": v.version,
                        "抓取": v.captured_at,
                        "SHA256": v.sha256,
                        "原始状态": json.loads(v.raw_json)["project_status"],
                    }
                    for v in versions
                ],
                hide_index=True,
            )
            with st.form("review_form_" + str(r["id"])):
                actor = st.text_input("审核人", key="actor_" + str(r["id"]))
                reason = st.text_input("审核原因/备注", key="reason_" + str(r["id"]))
                decision = st.selectbox(
                    "审核决定", ["confirmed", "rejected", "pending"], key="decision_" + str(r["id"])
                )
                if st.form_submit_button("保存审核"):
                    try:
                        with factory.begin() as session:
                            review(session, r["id"], mode, decision, reason, actor)
                        st.success("已记录审核（不自动核实事实字段）")
                    except ValueError as exc:
                        st.error(str(exc))
    st.download_button(
        "导出筛选结果 CSV",
        export.getvalue().encode("utf-8-sig"),
        file_name=f"{mode}-intelligence.csv",
        mime="text/csv",
    )


if page == "01 港口与物流":
    with factory() as session:
        render_ports(session, factory, mode)
elif page in ["统一情报中心", "02 海外产能与竞争", "03 物流市场与成本"]:
    st.subheader(page)
    if page.startswith("02"):
        st.info("计划、建设、试产、投产、延迟、取消分开；未核实状态为unknown。企业别名清单可配置。")
    if page.startswith("03"):
        st.info("实时运价、AIS和等待时间数据暂不可用；官方燃油周度观测与合同报价分开，不推断涨跌幅。")
    if page == "统一情报中心":
        render_decisions(factory, mode)
    list_items(None if page == "统一情报中心" else "capacity" if page.startswith("02") else "market")
elif page == "日报与周报":
    st.subheader("日报与周报")
    kind = st.selectbox("报告周期", ["daily", "weekly"])
    day = st.date_input("报告日期")
    if st.button("生成本空间报告"):
        from datetime import time

        from scm.settings import TIMEZONE

        with factory.begin() as session:
            generate_report(session, mode, kind, datetime.combine(day, time(), tzinfo=TIMEZONE))
            from scm.platform.decision_io import decision_report

            decision_report(session, mode, kind, datetime.combine(day, time(), tzinfo=TIMEZONE))
        st.success("报告已保存")
    with factory() as session:
        reports = list(
            session.scalars(
                select(Report)
                .where(Report.mode == mode)
                .order_by(Report.generated_at.desc(), Report.id.desc())
            )
        )
    if not reports:
        st.info("暂无报告；请按真实发布日期生成，不将历史文章冒充今日新闻。")
    for report in reports:
        with st.expander(f"{mode.upper()} · {report.kind} · {report.period_start}"):
            components.html(report.html, height=500, scrolling=True)
            st.download_button(
                "下载HTML",
                report.html,
                file_name=f"{mode}-{report.kind}-{report.id}.html",
                key="report_" + str(report.id),
                on_click="ignore",
            )
elif page == "预警收件箱":
    st.subheader("站内预警收件箱")
    st.caption("规则信号只表示待核实；不发送外部邮件或消息。")
    with factory() as session:
        alerts = list(session.scalars(select(Alert).where(Alert.mode == mode).order_by(Alert.id.desc())))
        for alert in alerts:
            ev = session.get(Evidence, alert.evidence_id)
            item = session.get(Item, ev.item_id)
            raw = json.loads(ev.raw_json)
            st.write(
                f"#{alert.id} {raw['title']} · {alert.state} · 证据版本{ev.version}"
                + (" · 旧版本预警" if ev.version != item.version else "")
            )
            choice = st.selectbox(
                "处理状态",
                ["pending", "read", "handled"],
                index=["pending", "read", "handled"].index(alert.state),
                key="alert_state_" + str(alert.id),
            )
            if st.button("更新状态", key="alert_save_" + str(alert.id)):
                with factory.begin() as writer:
                    set_alert(writer, alert.id, mode, choice)
                st.rerun()
    if mode in ["live", "demo"]:
        from scm.ports.service import read_alert

        with factory() as session:
            port_alerts = list(session.scalars(select(PortAlert).where(PortAlert.data_mode == mode)))
        st.markdown("### Module01 运营预警（沿用原服务）")
        for alert in port_alerts:
            st.write(f"港口预警 #{alert.id} · {alert.kind} · " + ("read" if alert.read_at else "pending"))
            if not alert.read_at and st.button("标记港口预警已读", key="port_alert_" + str(alert.id)):
                with factory.begin() as writer:
                    read_alert(writer, alert.id, mode)
                st.rerun()
    if not alerts:
        st.info("暂无本空间预警；不代表无风险。")
else:
    st.subheader("Sources 数据源")
    from scm.platform.decision_io import source_health

    with factory.begin() as health_session:
        st.dataframe(source_health(health_session), hide_index=True)
    st.caption("成功率仅为本库Live实际HTTP尝试样本；未请求为未知，DEMO不计入。")
    st.caption(
        "仅显式批准自动访问和全文复用且30日内核实的来源可请求；失败不循环重试。配置频率用于到期提示，尚未常驻调度。"
    )
    with factory() as session:
        sources = list(session.scalars(select(PlatformSource)))
        for source in sources:
            spec = json.loads(source.spec_json)
            with st.expander(source.id + " · " + spec.get("name", source.id)):
                st.json(
                    {
                        "adapter": spec.get("adapter"),
                        "module": spec.get("module"),
                        "permission": spec.get("reuse_policy", {}),
                        "coverage": spec.get("coverage", []),
                        "frequency_minutes": spec.get("frequency_minutes"),
                        "status": source.status,
                        "last_success": source.last_success_at,
                        "last_checked": source.last_checked_at,
                        "blocker": spec.get("blocker"),
                    }
                )
                st.link_button("官方来源/入口", spec["url"])
                if source.id in {x["id"] for x in specs()} and st.button(
                    "执行/测试单一来源", key="source_" + source.id, disabled=mode != "live"
                ):
                    result = collect(factory, [spec])
                    st.json(result)
                logs = list(
                    session.scalars(
                        select(Audit)
                        .where(Audit.source_id == source.id, Audit.mode == mode)
                        .order_by(Audit.id.desc())
                        .limit(5)
                    )
                )
                for log in logs:
                    st.json({"at": log.created_at, **json.loads(log.payload_json)})
    st.markdown("### 手动 CSV / Excel 导入（只进入 MANUAL）")
    st.download_button(
        "下载CSV模板",
        (ROOT / "config/platform_import.template.csv").read_bytes(),
        file_name="platform_import.template.csv",
    )
    upload = st.file_uploader("上传CSV或XLSX（无公司敏感数据）", type=["csv", "xlsx"])
    if upload and st.button("导入至 MANUAL"):
        try:
            st.json(import_file(factory, upload.getvalue(), upload.name))
        except Exception as exc:
            st.error(type(exc).__name__ + ": " + str(exc)[:220])
