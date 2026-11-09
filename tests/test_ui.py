from datetime import date

import pytest
from streamlit.testing.v1 import AppTest

from scm.collectors.service import load_demo
from scm.reports.service import generate_report
from scm.settings import ROOT
from scm.shipments.service import import_csv


@pytest.fixture
def dashboard(tmp_path, monkeypatch):
    import scm.database.session as module

    url = "sqlite:///" + str(tmp_path / "ui.db")
    monkeypatch.setattr(module, "DATABASE_URL", url)
    # default argument was bound at import; replace UI's factory function before run.
    original = module.session_factory
    monkeypatch.setattr(module, "session_factory", lambda: original(url))
    factory = original(url)
    load_demo(factory)
    with factory.begin() as s:
        import_csv(s, (ROOT / "fixtures/demo_shipments.csv").read_text(), "demo")
        generate_report(s, "daily", "demo", date(2026, 11, 6))
    app = AppTest.from_file(str(ROOT / "src/scm/ui/app.py"), default_timeout=30)
    app.run()
    return app


@pytest.mark.parametrize(
    "page", ["Overview", "Intelligence", "Port Monitor", "Shipment Monitor", "Reports", "Sources & System"]
)
def test_all_six_demo_pages(dashboard, page):
    app = dashboard
    app.sidebar.radio[0].set_value("演示数据 Demo").run()
    app.sidebar.radio[1].set_value(page).run()
    assert not app.exception
    assert any("演示空间" in w.value for w in app.warning)
    if page == "Overview":
        assert app.metric[0].value == "0"  # Unreviewed Demo content is not confirmed current disruption.
        assert any("当前空间共 5 条" in c.value for c in app.caption)
    if page == "Shipment Monitor":
        assert any("DEMO-0001" in e.label for e in app.expander)


def test_live_overview_never_shows_demo(dashboard):
    assert not dashboard.exception
    assert dashboard.metric[0].value == "0"
    assert not dashboard.expander


def test_port_selection_and_override(dashboard):
    app = dashboard
    app.sidebar.radio[0].set_value("演示数据 Demo").run()
    app.sidebar.radio[1].set_value("Port Monitor").run()
    app.selectbox(key="port01_choice").set_value("hamburg").run()
    next(x for x in app.selectbox if x.label == "选择港口").set_value("Hamburg").run()
    assert any("Hamburg" in m.label for m in app.metric)
    next(x for x in app.selectbox if x.label == "调整等级").set_value("高")
    next(x for x in app.text_input if x.label == "调整人").set_value("test planner")
    next(x for x in app.text_input if x.label == "调整原因（必填）").set_value(
        "Manual carrier confirmation pending"
    )
    next(x for x in app.button if x.label == "保存人工状态").click().run()
    assert not app.exception
    assert next(m for m in app.metric if m.label == "Hamburg · 公告规则提示").value == "高"
    assert next(m for m in app.metric if m.label == "Hamburg · 运营严重度").value == "未知"


def test_live_ui_surfaces_coverage_warning(dashboard):
    assert any("采集覆盖不足" in warning.value for warning in dashboard.warning)


def test_event_detail_shows_lifecycle_evidence_and_uncertainty(dashboard):
    app = dashboard
    app.sidebar.radio[0].set_value("演示数据 Demo").run()
    assert not app.exception
    assert any("生命周期" in m.value and "来源可信度" in m.value for m in app.markdown)
    assert any("独立政策日期" in m.value for m in app.markdown)
