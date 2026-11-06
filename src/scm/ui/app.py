"""ESCIM enterprise command center. Presentation-only; existing services stay authoritative."""

from html import escape

import streamlit as st
from sqlalchemy import select

from scm.collectors.coverage import collection_coverage
from scm.collectors.service import load_demo, register_sources
from scm.database import session as database_session
from scm.database.models import Event, Source
from scm.database.session import session_factory
from scm.intelligence.service import reassess_events
from scm.reports.service import period_bounds
from scm.settings import ROOT
from scm.shipments.service import import_csv
from scm.ui import pages
from scm.ui.presentation import NAVIGATION, build_views, dashboard_counts, freshness, local_time
from scm.ui.theme import CSS

st.set_page_config(page_title="ESCIM · 供应链例外与风险指挥台", page_icon="◈", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource
def get_factory(database_scope):
    """Include configured DB identity in resource cache to prevent cross-DB UI reuse."""
    factory = session_factory()
    with factory.begin() as session:
        register_sources(session)
        reassess_events(session)
    return factory


factory = get_factory(database_session.DATABASE_URL)
st.sidebar.markdown(
    '<div class="scm-brand"><span class="scm-mark">E</span><div><strong>ESCIM</strong><small>供应链情报 · 本地指挥台</small></div></div>',
    unsafe_allow_html=True,
)
mode_label = st.sidebar.radio("数据空间", ["真实数据 Live", "演示数据 Demo"])
mode = "demo" if "Demo" in mode_label else "live"
page = st.sidebar.radio("工作台", list(NAVIGATION), format_func=lambda key: NAVIGATION[key])
st.sidebar.caption("规则分析 · 证据优先\n\n无LLM：中文模板与原文摘录，非全文翻译。Asia/Shanghai。")
if mode == "demo" and st.sidebar.button("加载/刷新演示Fixtures"):
    load_demo(factory)
    with factory.begin() as writer:
        import_csv(writer, (ROOT / "fixtures/demo_shipments.csv").read_text(encoding="utf-8"), "demo")
    st.rerun()
st.title("供应链例外与风险指挥台")

with factory() as session:
    events = list(session.scalars(select(Event).where(Event.data_mode == mode)))
    source_rows = list(session.scalars(select(Source)))
    views = build_views(session, events, mode)
    counts = dashboard_counts(views)
    coverage = collection_coverage(session, *period_bounds("daily"))
    if mode == "demo":
        context = "演示记录 · 不计入真实来源覆盖"
        latest = max((e.fetched_at for e in events if e.fetched_at), default=None)
    else:
        context = f"今日采集覆盖 {coverage['covered_sources']}/{coverage['configured_sources']} 个启用来源 · 有限样本"
        latest = max(
            (s.last_success_at for s in source_rows if s.enabled and s.last_success_at), default=None
        )
    st.markdown(
        f'<div class="scm-context {mode}"><span class="scm-mode">{"DEMO · 虚构数据" if mode == "demo" else "LIVE · 真实来源"}</span>{escape(context)}<br>最近成功记录 {local_time(latest)}（Asia/Shanghai） · {freshness(latest)} · 不是实时运行状态</div>',
        unsafe_allow_html=True,
    )
    if mode == "demo":
        st.warning("演示空间：全部示例新闻/航次为虚构；确认指标与告警仅演示，不代表真实运营。")
    elif not coverage["adequate"]:
        st.warning(
            f"今日采集覆盖不足（{coverage['covered_sources']}/{coverage['configured_sources']}）；不能据缺少记录判断无重要新闻或港口正常。"
        )
    if "scm_flash" in st.session_state:
        st.success(st.session_state.pop("scm_flash"))
    if page == "Overview":
        pages.overview(session, views, factory, mode, counts)
    elif page == "Intelligence":
        pages.intelligence(session, views, factory, mode)
    elif page == "Port Monitor":
        pages.ports(session, views, factory, mode)
    elif page == "Shipment Monitor":
        pages.shipments(session, factory, mode)
    elif page == "Reports":
        pages.reports(session, factory, mode)
    else:
        pages.sources(session, factory, mode, source_rows, coverage)
