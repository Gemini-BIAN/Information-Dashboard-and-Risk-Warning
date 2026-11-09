from streamlit.testing.v1 import AppTest

from scm.ports.registry import registry
from scm.settings import ROOT


def test_all_12_detail_switches_unknown_not_normal(tmp_path, monkeypatch):
    import scm.database.session as module

    url = "sqlite:///" + str(tmp_path / "port01.db")
    original = module.session_factory
    monkeypatch.setattr(module, "DATABASE_URL", url)
    monkeypatch.setattr(module, "session_factory", lambda: original(url))
    app = AppTest.from_file(str(ROOT / "src/scm/ui/app.py"), default_timeout=30).run()
    app.sidebar.radio[1].set_value("Port Monitor").run()
    for port in registry().ports:
        app.selectbox(key="port01_choice").set_value(port.id).run()
        assert not app.exception
        assert any(port.business_label in m.value for m in app.markdown)
        assert any("未知" in m.value for m in app.markdown)
    app.text_input(key="port01_search").set_value("Dover").run()
    assert app.selectbox(key="port01_choice").value == "dover"


def test_country_filter_retains_distinct_uk_locations(tmp_path, monkeypatch):
    import scm.database.session as module

    url = "sqlite:///" + str(tmp_path / "filter.db")
    original = module.session_factory
    monkeypatch.setattr(module, "DATABASE_URL", url)
    monkeypatch.setattr(module, "session_factory", lambda: original(url))
    app = AppTest.from_file(str(ROOT / "src/scm/ui/app.py"), default_timeout=30).run()
    app.sidebar.radio[1].set_value("Port Monitor").run()
    app.multiselect(key="port01_countries").set_value(["UK"]).run()
    assert not app.exception
    assert app.selectbox(key="port01_choice").options == ["TEESPORT", "MIDDLESBROUGH", "FELIXSTOWE", "DOVER"]
