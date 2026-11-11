from streamlit.testing.v1 import AppTest

from scm.settings import ROOT


def test_platform_pages_and_namespaces(tmp_path, monkeypatch):
    monkeypatch.setenv("SCM_PLATFORM_DATABASE_URL", "sqlite:///" + str(tmp_path / "platform.db"))
    app = AppTest.from_file(str(ROOT / "src/scm/platform/app.py"), default_timeout=30).run()
    assert not app.exception
    assert any("暂无匹配" in x.value for x in app.info)
    app.sidebar.radio(key="platform_mode").set_value("demo").run()
    next(b for b in app.sidebar.button if b.label == "加载 DEMO 合成数据").click().run()
    for name in [
        "02 海外产能与竞争",
        "03 物流市场与成本",
        "日报与周报",
        "预警收件箱",
        "Sources 数据源",
        "01 港口与物流",
    ]:
        app.sidebar.radio(key="platform_page").set_value(name).run()
        assert not app.exception, name
    app.sidebar.radio(key="platform_page").set_value("统一情报中心").run()
    assert any("DEMO project delayed" in x.label for x in app.expander)
    app.sidebar.radio(key="platform_mode").set_value("live").run()
    assert not app.exception
    assert not any("DEMO project delayed" in x.label for x in app.expander)
    app.sidebar.radio(key="platform_mode").set_value("manual").run()
    assert not app.exception
    assert any("暂无匹配" in x.value for x in app.info)
