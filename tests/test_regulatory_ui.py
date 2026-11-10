from streamlit.testing.v1 import AppTest

from scm.settings import ROOT


def test_missing_research_empty_library_never_answers_from_model(tmp_path, monkeypatch):
    monkeypatch.setenv("SCM_REGULATORY_DATABASE_URL", "sqlite:///" + str(tmp_path / "library.db"))
    monkeypatch.setenv("SCM_REGULATORY_STORAGE", str(tmp_path / "files"))
    monkeypatch.setenv("SCM_REGULATORY_RESEARCH", str(tmp_path / "absent-research"))
    app = AppTest.from_file(str(ROOT / "src/scm/regulatory/app.py"), default_timeout=30).run()
    assert not app.exception
    assert sum("BLOCKED" in x.value for x in app.markdown) == 5
    for question in [
        "2023/1542 Article 7 碳足迹要求",
        "REACH与CLP对供应商有什么要求",
        "ISO Tank在欧洲运输需核查危险品规则",
    ]:
        app.text_input(key="empty_question").set_value(question)
        app.button[0].click().run()
        assert not app.exception
        assert any("证据不足" in w.value for w in app.warning)
        assert not app.code
