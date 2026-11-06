from datetime import timedelta
from html import escape

import streamlit as st
from sqlalchemy import select

from scm.database.models import Analysis, RawRevision, ReviewLog, Source
from scm.exports import safe_csv
from scm.intelligence.service import review
from scm.risk.lifecycle import LIFECYCLE_LABELS
from scm.settings import TIMEZONE, utcnow
from scm.ui.presentation import REVIEWS, decoded, export_rows, filter_views, local_time


def pill(text, color=""):
    return f'<span class="scm-pill {color}">{escape(str(text))}</span>'


def empty(title, explanation):
    st.markdown(
        f'<div class="scm-empty"><strong>{escape(title)}</strong>{escape(explanation)}</div>',
        unsafe_allow_html=True,
    )


def filters(views, mode, page):
    prefix = f"{mode}:{page}"
    with st.expander("筛选与搜索", expanded=page == "Intelligence"):
        query = st.text_input("搜索情报", placeholder="标题、来源、关键词或事件 ID", key=prefix + ":query")
        c = st.columns(4)
        country = c[0].selectbox(
            "国家 / 港口",
            ["全部"]
            + sorted(
                {
                    x
                    for v in views
                    for x in decoded(v.event.countries_json, []) + decoded(v.event.ports_json, [])
                }
            ),
            key=prefix + ":country",
        )
        category = c[1].selectbox(
            "事件类型", ["全部"] + sorted({v.event.event_type for v in views}), key=prefix + ":type"
        )
        severity = c[2].selectbox("内容严重度", ["全部", "高", "中", "低", "未知"], key=prefix + ":severity")
        review_status = c[3].selectbox(
            "审核状态",
            ["全部", "pending", "confirmed", "rejected"],
            format_func=lambda v: REVIEWS.get(v, v),
            key=prefix + ":review",
        )
        c = st.columns([2, 1])
        period = c[0].date_input(
            "发布日期范围",
            value=(
                utcnow().astimezone(TIMEZONE).date() - timedelta(days=30),
                utcnow().astimezone(TIMEZONE).date(),
            ),
            key=prefix + ":period",
        )
        lifecycle = c[1].selectbox(
            "运营生命周期",
            ["全部"] + list(LIFECYCLE_LABELS),
            format_func=lambda v: LIFECYCLE_LABELS.get(v, v),
            key=prefix + ":lifecycle",
        )
        c = st.columns(2)
        unknown = c[0].checkbox("包括发布日期未知", True, key=prefix + ":unknown")
        rejected = c[1].checkbox("包括已驳回", False, key=prefix + ":rejected")
    return filter_views(
        views,
        query=query,
        country=country,
        category=category,
        severity=severity,
        review=review_status,
        lifecycle=lifecycle,
        period=period,
        include_unknown=unknown,
        include_rejected=rejected,
    )


def card(session, view, factory):
    e = view.event
    ports = decoded(e.ports_json, [])
    region = " / ".join(decoded(e.countries_json, []) + ports) or "地域未识别"
    severity_color = "red" if e.risk_level == "高" else "amber" if e.risk_level == "中" else ""
    priority_color = "teal" if view.confirmed_current else "amber" if view.tier == 1 else ""
    confidence = "演示证据" if e.data_mode == "demo" else "公开来源 · 未独立鉴真"
    with st.container(border=True, key=f"scm_event_{e.id}"):
        st.markdown(
            '<div class="scm-card-head">'
            + pill(view.priority, priority_color)
            + pill("内容" + e.risk_level, severity_color)
            + pill(LIFECYCLE_LABELS.get(e.lifecycle, "未知"))
            + pill(REVIEWS.get(e.review_status, e.review_status))
            + "</div>"
            + f'<div class="scm-event-title">{escape(view.title)}</div><div class="scm-summary">规划提示（推测）：{escape(view.summary)}</div>'
            + f'<div class="scm-meta">{escape(e.event_type)} · {escape(region)} · {escape(view.relevance_reason)} · {escape(confidence)}</div>'
            + f'<div class="scm-meta">#{e.id} · 来源 {escape(e.source_id)} · 发布 {local_time(e.published_at)} · 抓取 {local_time(e.fetched_at)}（Asia/Shanghai）</div>',
            unsafe_allow_html=True,
        )
        st.link_button("查看原始来源", e.canonical_url, key=f"source-{e.id}")
        with st.expander(f"#{e.id} · 查看事实、依据与审核"):
            st.write(
                f"生命周期：{LIFECYCLE_LABELS.get(e.lifecycle, e.lifecycle)} ｜ 来源可信度：{e.source_confidence} ｜ 规则：{e.rule_version}"
            )
            st.write(
                f"内容严重度 {e.risk_level} ≠ 当前运营实况；当前确认条件：24h内发布与抓取、最新规则、明确active港口证据且人工确认（自报）。"
            )
            if not view.confirmed_current:
                st.warning("未满足当前已确认运营中断条件；不自动升级未知、宣布、历史或未审证据。")
            st.write(
                f"政策状态：{e.policy_status} ｜ 独立政策日期：生效 {e.effective_at or '未知'} / 到期 {e.expiry_at or '未知'} / 废止 {e.repeal_at or '未知'}"
            )
            for reason in decoded(e.policy_reasons_json, []):
                st.caption(reason)
            for fact in view.payload.get("facts", []):
                st.markdown("**核心事实 · 原文依据**")
                st.write(fact["text_zh"])
                st.text(fact["quote"])
            for label, key in [
                ("潜在业务影响（推测）", "potential_impacts"),
                ("关注指标", "watch_indicators"),
                ("建议核实 / 下一步行动", "suggested_actions"),
            ]:
                st.markdown("**" + label + "**")
                for value in view.payload.get(key, []):
                    st.write(value)
            if view.payload.get("title_zh") and view.title != view.payload["title_zh"]:
                st.caption(
                    "已保存分析标题：" + view.payload["title_zh"] + "；仅调整UI展示措辞，业务相关性仍需核实。"
                )
            st.markdown("**规则分级与生命周期依据**")
            for reason in decoded(e.risk_reasons_json, []):
                st.write(reason)
            st.caption(view.payload.get("quality_note", ""))
            analysis = session.scalar(
                select(Analysis).where(Analysis.event_id == e.id).order_by(Analysis.id.desc())
            )
            if analysis:
                st.caption(
                    "分析时间："
                    + local_time(analysis.analyzed_at)
                    + "（Asia/Shanghai） · Provider "
                    + analysis.provider
                )
                if analysis.error:
                    st.warning("Provider回退：" + analysis.error)
            source = session.get(Source, e.source_id)
            reuse = decoded(source.audit_json, {}).get("reuse_policy", {}) if source else {}
            if reuse.get("license") == "CC BY 4.0":
                st.caption(
                    "© European Union — CC BY 4.0；已抽取正文并加入中文规则模板/分析，修改不代表欧盟立场。"
                )
                st.link_button(
                    "欧委会复用许可", "https://commission.europa.eu/legal-notice_en", key=f"license-{e.id}"
                )
            raw = session.scalar(
                select(RawRevision).where(
                    RawRevision.event_id == e.id, RawRevision.content_hash == e.content_hash
                )
            )
            if raw:
                st.download_button("下载原始正文", raw.body, file_name=f"event-{e.id}.txt", key=f"raw-{e.id}")
            st.markdown("**审核与行动记录**")
            st.caption(
                "确认只记录审核判断，不修改原始事实或运营生命周期；备注可记录负责人、核实事项与下一步。审核人为自报身份。"
            )
            with st.form(f"review-{e.id}"):
                action = st.selectbox(
                    "审核操作",
                    ["confirmed", "rejected", "pending", "note"],
                    format_func=lambda v: {**REVIEWS, "note": "仅备注"}.get(v, v),
                )
                actor = st.text_input("审核人")
                reason = st.text_area("原因/备注（必填）")
                if st.form_submit_button("保存审核记录"):
                    try:
                        with factory.begin() as writer:
                            review(writer, e.id, action, actor, reason)
                        st.session_state["scm_flash"] = "审核/行动记录已保存"
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            logs = session.scalars(
                select(ReviewLog)
                .where(
                    ReviewLog.target_type == "event",
                    ReviewLog.target_id == str(e.id),
                    ReviewLog.data_mode == e.data_mode,
                )
                .order_by(ReviewLog.id.desc())
                .limit(10)
            ).all()
            if logs:
                for log in logs:
                    st.caption(f"{local_time(log.created_at)} · {log.actor} · {log.action}")
                    st.text(log.reason)
            else:
                st.caption("暂无审核 / 行动记录，待团队核实。")


def queue(session, views, factory, mode, page):
    selected = filters(views, mode, page)
    size = 8 if page == "Overview" else 20
    c = st.columns([6, 2, 1])
    c[0].caption(
        f"匹配 {len(selected)} 条 · 排序：确认状态 → 相关性 → 发布时间 → 内容严重度。非实时告警不升为当前中断。"
    )
    c[1].download_button(
        "导出筛选结果 CSV",
        safe_csv(export_rows(selected)),
        file_name=f"intelligence-{mode}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    page_number = c[2].number_input(
        "队列页码",
        min_value=1,
        max_value=max(1, (len(selected) + size - 1) // size),
        value=1,
        key=f"{mode}:{page}:pagination",
        label_visibility="collapsed",
        help="每页8条总览或20条研判记录",
    )
    if not selected:
        empty("当前没有匹配的情报", "调整筛选条件或核实采集覆盖；没有记录不表示没有风险。")
        return
    for view in selected[(page_number - 1) * size : page_number * size]:
        card(session, view, factory)
