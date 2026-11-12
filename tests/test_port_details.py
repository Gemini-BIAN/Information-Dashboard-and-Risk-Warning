import hashlib
from datetime import timedelta

import pytest
from streamlit.testing.v1 import AppTest

from scm.database.models import RawRevision
from scm.platform.demo import seed
from scm.ports.detail import detail, profile, save_profile
from scm.ports.engine import Notice
from scm.ports.registry import registry
from scm.ports.service import store_notice
from scm.settings import ROOT, utcnow


def test_all_ports_empty_unknown_and_business_profile_isolated(factory):
    with factory.begin() as s:
        for p in registry().ports:
            d = detail(s, p.id, "live")
            assert d["snapshot"]["state"] == "unknown" and not d["records"]
            assert d["profile"].usage == ""
        save_profile(
            s,
            "dover",
            "demo",
            dict(
                usage="DEMO only",
                routes="DEMO route",
                cargo="DEMO cargo",
                transport="ISO Tank",
                alternatives=["hamburg"],
            ),
            "tester",
            "synthetic configuration",
        )
        assert profile(s, "dover", "demo").usage == "DEMO only"
        assert profile(s, "dover", "live").usage == "" and profile(s, "hamburg", "demo").usage == ""
        assert profile(s, "dover", "manual").usage == ""
        with pytest.raises(ValueError):
            save_profile(s, "dover", "live", dict(alternatives=["dover"]), "tester", "bad")
        with pytest.raises(ValueError):
            detail(s, "missing", "live")
        with pytest.raises(ValueError):
            detail(s, "dover", "invalid")
        assert detail(s, "dover", "demo")["snapshot"]["state"] == "unknown"


def test_notice_versions_canonical_change_evidence_and_history_not_current(factory):
    now = utcnow()
    spec = dict(
        id="demo-detail",
        name="DEMO evidence",
        url="https://example.invalid/feed",
        ports=["dover"],
        audit_ref="DEMO",
    )

    def notice(url, body, days):
        return Notice(
            external_id="DEMO-DETAIL",
            title="DEMO Dover closure",
            body=body,
            url=url,
            published_at=now - timedelta(days=days),
            fetched_at=now,
            valid_from=now - timedelta(days=days),
            valid_until=now - timedelta(days=days - 1),
            data_mode="demo",
            verification_type="DEMO",
        )

    with factory.begin() as s:
        store_notice(
            s, spec, notice("https://example.invalid/first", "Dover port is closed. DEMO only.", 10), now
        )
        store_notice(
            s,
            spec,
            notice("https://example.invalid/updated", "Dover closure lifted. DEMO operations resumed.", 9),
            now,
        )
        data = detail(s, "dover", "demo")
        assert len(data["records"]) == 2
        assert all(not r["current"] for r in data["records"])
        assert data["snapshot"]["state"] != "confirmed_normal"
        for record in data["records"]:
            raw = s.get(RawRevision, int(record["id"].split("-")[1]))
            assert record["sha256"] == raw.content_hash
            assert record["body_sha256"] == hashlib.sha256(raw.body.encode("utf-8")).hexdigest()
            assert record["body"] == raw.body and record["assessment_id"]
        assert not detail(s, "dover", "live")["records"]


def test_port_detail_ui_all12_tabs_return_and_namespace(tmp_path, monkeypatch):
    import scm.ui.port_details as ui

    monkeypatch.setenv("SCM_PLATFORM_DATABASE_URL", "sqlite:///" + str(tmp_path / "ui.db"))
    event = {"value": None}
    monkeypatch.setattr(ui, "WORLD_MAP", lambda **kwargs: event["value"])
    app = AppTest.from_file(str(ROOT / "src/scm/platform/app.py"), default_timeout=30).run()
    app.sidebar.radio(key="platform_page").set_value("01 港口与物流").run()
    assert not app.tabs and not app.selectbox and not app.metric
    assert not any("港口监测" == x.value for x in app.subheader)
    for number, port in enumerate(registry().ports, 1):
        event["value"] = {
            "action": "details",
            "port_id": port.id,
            "view": {"center": [port.latitude, port.longitude], "zoom": 9},
            "event_id": number,
        }
        app.run()
        assert not app.exception, port.id
        assert [t.label for t in app.tabs] == ["概览", "公告时间线", "来源证据", "业务影响"]
        assert any("企业业务影响：未知" in x.value for x in app.info)
        app.run()
        event["value"] = None
        app.button(key="port_detail_back").click().run()
        assert not app.tabs and not app.selectbox
        assert app.session_state["port_detail_selected"] == port.id
        assert app.session_state["port_world_view"]["zoom"] == 9
    app.sidebar.radio(key="platform_mode").set_value("manual").run()
    assert not app.exception and not app.tabs
    app.sidebar.radio(key="platform_page").set_value("统一情报中心").run()
    app.sidebar.radio(key="platform_page").set_value("01 港口与物流").run()
    assert not app.tabs and app.session_state["port_world_view"] is None


def test_demo_projection_never_becomes_live(factory):
    seed(factory)
    with factory() as s:
        d = detail(s, "dover", "demo")
        assert d["records"] and d["alerts"]
        assert not detail(s, "dover", "live")["records"]
        assert not detail(s, "dover", "manual")["records"]
