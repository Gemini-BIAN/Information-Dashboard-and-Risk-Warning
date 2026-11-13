"""Decision support display; kept out of the pure-map page."""

import json

import streamlit as st
from sqlalchemy import select

from scm.platform.decision import STATES, attest_facts, cards, handle, links
from scm.platform.decision_io import import_links
from scm.platform.models import Audit
from scm.settings import ROOT


def render(factory, mode):
    st.markdown("### 决策支持 · 事实 / 推断 / 业务声明 / 行动分开")
    important = st.checkbox("仅高价值事件", value=True, key="decision_important")
    with factory.begin() as session:
        data = cards(session, mode, important)
    if not data:
        st.info("暂无合格决策事件；可关闭筛选查看背景/待核实记录，覆盖不足不代表无风险。")
    for c in data:
        if not c.get("entity_representative", True):
            continue
        with st.expander(f"决策 #{c['card_id']} · {c['title']} · {c['handling_state']}"):
            st.caption(
                f"{mode.upper()} · 证据版本{c['version']} · {c['event']['validity']} · 规则{c['rule_version']}"
            )
            st.write(
                "严重度："
                + c["severity"]
                + "；业务相关度："
                + c["business_relevance"]
                + "；影响程度："
                + c["impact_level"]
            )
            st.write(c["severity_reason"])
            st.caption(
                f"发布：{c['published_at'] or '未知'} · 观测：{c.get('observed_at') or '未知'} · 采集：{c['fetched_at']}"
            )
            st.json(c["source_quality"])
            st.markdown("**已核实事实（人工声明，非独立外部验证）**")
            st.json(c["verified_facts"]) if c["verified_facts"] else st.caption(
                "无已核实事实；未把采集成功当作业务核实。"
            )
            st.markdown("**来源主张 / 结构化提取（规则，待核实）**")
            st.json(c["event"])
            st.json(c["structured_extraction"])
            if c.get("entity_summary"):
                st.markdown("**同一事件/项目时间线与来源差异**")
                entity = c["entity_summary"]
                st.caption(entity["note"])
                st.dataframe([
                    {"来源日期": r["raw"].get("status_at") or r["raw"]["published_at"],
                     "阶段/状态": r["raw"].get("project_status") if r["raw"]["module"] == "capacity"
                     else r["raw"].get("operational_status"),
                     "产能值": r["raw"].get("capacity"), "单位": r["raw"].get("capacity_unit"),
                     "产能口径": r["raw"].get("capacity_basis"), "来源": r["raw"]["url"],
                     "证据版本": r["version"]} for r in entity["timeline"]
                ], hide_index=True)
                if entity.get("conflicts") or entity.get("conflict"):
                    st.warning("来源存在差异，保留全部主张，须人工核实。")
            st.caption(c["normalization_note"])
            for f in c["facts"]:
                st.code(f["quote"], language=None)
            st.markdown("**未核实假设**")
            st.json(c["hypotheses"])
            st.markdown("**用户提供业务关联**")
            st.json(c["user_context"])
            st.markdown("**潜在影响（推断）**")
            st.write(c["impact"])
            st.markdown("**关键未知 / 建议核实**")
            for t in c["missing"] + c["verification_tasks"]:
                st.write("· " + t)
            st.markdown("**候选行动（待人工决策）**")
            for action in c["candidate_actions"]:
                st.write("· " + action)
            st.link_button("原文与证据", c["source_url"])
            st.caption("SHA256 " + c["sha256"])
            with st.form("decision_handle_" + str(c["card_id"])):
                state = st.radio(
                    "人工处理状态",
                    STATES,
                    index=STATES.index(c["handling_state"]),
                    horizontal=True,
                    format_func=lambda value: {
                        "pending": "待处理",
                        "confirmed": "已确认",
                        "ignored": "忽略",
                        "in_progress": "处理中",
                        "resolved": "已处理",
                    }[value],
                )
                actor = st.text_input("处理人")
                reason = st.text_input("处理原因/反馈")
                verified = st.checkbox("我已人工核实下列全部非假设引文主张；处理确认不自动等于事实核实")
                if st.form_submit_button("保存处理与反馈"):
                    try:
                        with factory.begin() as session:
                            handle(session, c["card_id"], mode, state, actor, reason)
                            if verified:
                                attest_facts(
                                    session,
                                    c["card_id"],
                                    mode,
                                    [f["quote"] for f in c["facts"]],
                                    actor,
                                    reason,
                                )
                        st.success("处理/核实声明已审计；新证据版本需重新审核。")
                    except ValueError as exc:
                        st.error(str(exc))
            with factory() as session:
                log = list(
                    session.scalars(
                        select(Audit)
                        .where(Audit.mode == mode, Audit.source_id == "decision-card-" + str(c["card_id"]))
                        .order_by(Audit.id.desc())
                    )
                )
            if log:
                st.json([{"at": r.created_at, **json.loads(r.payload_json)} for r in log])
    with st.expander("脱敏业务关联配置 / CSV或Excel导入"):
        st.caption(
            "不上传敏感订单/客户/真实报价；字段为用户声明，不自动认定实际业务。每次导入原子替换本空间关联，完整审计。"
        )
        with factory() as session:
            st.json([x.model_dump() for x in links(session, mode)])
        st.download_button(
            "下载关联CSV模板",
            (ROOT / "config/decision_links.template.csv").read_bytes(),
            file_name="decision_links.template.csv",
        )
        file = st.file_uploader("脱敏关联CSV/XLSX", type=["csv", "xlsx"], key="decision_links_upload")
        actor = st.text_input("关联配置人", key="decision_link_actor")
        reason = st.text_input("关联修改原因", key="decision_link_reason")
        if file and st.button("导入本空间业务关联"):
            try:
                st.success(import_links(factory, file.getvalue(), file.name, mode, actor, reason))
            except ValueError as exc:
                st.error(str(exc))
