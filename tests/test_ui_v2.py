"""Synthetic and Demo UI tests; never evidence of actual live disruptions."""

import json
import tomllib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from streamlit.testing.v1 import AppTest

from scm.collectors.service import load_demo
from scm.database.models import Event, RawRevision, ReviewLog, ShipmentSnapshot
from scm.reports.service import generate_report
from scm.risk.lifecycle import RULE_VERSION
from scm.settings import ROOT
from scm.shipments.service import import_csv
from scm.ui.pages import import_upload
from scm.ui.presentation import (
    current_confirmed,
    dashboard_counts,
    export_rows,
    filter_views,
    freshness,
    make_view,
    sort_views,
)

NOW = datetime(2026, 11, 6, 8, tzinfo=timezone.utc)


def event(**changes):
    values = {
        "id": 1,
        "title": "Synthetic Rotterdam operations suspended",
        "data_mode": "live",
        "published_at": NOW.isoformat(),
        "fetched_at": NOW.isoformat(),
        "risk_level": "高",
        "review_status": "confirmed",
        "lifecycle": "active",
        "rule_version": RULE_VERSION,
        "event_type": "港口运营",
        "countries_json": '["荷兰"]',
        "ports_json": '["Rotterdam"]',
        "port_signals_json": json.dumps({"Rotterdam": {"lifecycle": "active", "severity": "高"}}),
        "source_id": "synthetic-test",
        "canonical_url": "https://official.test/synthetic",
    }
    values.update(changes)
    return SimpleNamespace(**values)


@pytest.mark.parametrize(
    "changes",
    [
        {"review_status": "pending"},
        {"review_status": "rejected"},
        {"lifecycle": "unknown"},
        {"lifecycle": "announced"},
        {"lifecycle": "resolved"},
        {"lifecycle": "cancelled"},
        {"rule_version": "legacy"},
        {"event_type": "关税贸易"},
        {"ports_json": "[]"},
        {"port_signals_json": "{}"},
        {"published_at": None},
        {"fetched_at": None},
        {"published_at": (NOW - timedelta(hours=25)).isoformat()},
        {"fetched_at": (NOW - timedelta(hours=25)).isoformat()},
        {"published_at": (NOW + timedelta(minutes=1)).isoformat()},
        {"port_signals_json": json.dumps({"Rotterdam": {"lifecycle": "unknown", "severity": "高"}})},
    ],
)
def test_content_high_never_implies_confirmed_current(changes):
    assert not current_confirmed(event(**changes), NOW)


def test_positive_current_confirmation_requires_all_evidence_and_does_not_change_it():
    original = event()
    assert current_confirmed(original, NOW)
    assert original.lifecycle == "active" and original.risk_level == "高"
    counts = dashboard_counts(
        [
            make_view(original, now=NOW),
            make_view(event(id=2, review_status="pending", lifecycle="unknown"), now=NOW),
        ]
    )
    assert counts == {"total": 2, "current": 1, "unverified": 1, "high_content": 2, "pending": 1}


def test_order_is_explainable_and_historical_high_content_cannot_lead():
    historical = make_view(event(id=3, published_at=(NOW - timedelta(days=60)).isoformat()), now=NOW)
    unclear = make_view(event(id=2, review_status="pending", lifecycle="unknown"), now=NOW)
    verified = make_view(event(id=1), now=NOW)
    assert [v.event.id for v in sort_views([historical, unclear, verified])] == [1, 2, 3]
    assert "实时告警" in unclear.priority and historical.tier == 3


def test_unknown_time_and_future_are_explicit_not_fresh():
    assert "未来" in freshness((NOW + timedelta(days=1)).isoformat(), NOW)
    assert "未取得" in freshness(None, NOW)
    assert "陈旧" in freshness((NOW - timedelta(days=2)).isoformat(), NOW)


def test_filters_and_csv_keep_risk_taxonomy_and_provenance():
    rows = [
        make_view(event(), now=NOW),
        make_view(event(id=2, data_mode="demo", lifecycle="unknown", review_status="pending"), now=NOW),
    ]
    assert (
        len(filter_views(rows, country="Rotterdam", severity="高", review="pending", lifecycle="unknown"))
        == 1
    )
    assert not filter_views(rows, query="not-matching")
    result = export_rows(rows)
    assert result[0]["source_url"] and result[0]["confirmed_current_operational"] is True
    assert result[1]["data_mode"] == "demo" and result[1]["confirmed_current_operational"] is False
    assert result[0]["risk_level"] == result[0]["content_severity"]  # legacy CSV column retained


def app_for(factory, monkeypatch):
    import scm.database.session as session_module

    monkeypatch.setattr(session_module, "session_factory", lambda: factory)
    monkeypatch.setattr(session_module, "DATABASE_URL", str(factory.kw["bind"].url))
    return AppTest.from_file(str(ROOT / "src/scm/ui/app.py"), default_timeout=30).run()


@pytest.mark.parametrize("mode", ["真实数据 Live", "演示数据 Demo"])
@pytest.mark.parametrize(
    "page", ["Overview", "Intelligence", "Port Monitor", "Shipment Monitor", "Reports", "Sources & System"]
)
def test_all_v2_pages_both_modes(factory, monkeypatch, mode, page):
    load_demo(factory)
    with factory.begin() as s:
        import_csv(s, (ROOT / "fixtures/demo_shipments.csv").read_text(encoding="utf-8"), "demo")
        generate_report(s, "daily", "demo")
        generate_report(s, "daily", "live")
    app = app_for(factory, monkeypatch)
    app.sidebar.radio[0].set_value(mode).run()
    app.sidebar.radio[1].set_value(page).run()
    assert not app.exception
    if "Live" in mode:
        assert not any("演示空间" in w.value for w in app.warning)
    else:
        assert any("演示空间" in w.value for w in app.warning)
    if page == "Overview":
        assert app.metric[0].value == "0"


def test_empty_live_shows_insufficient_coverage_and_meaningful_action(factory, monkeypatch):
    app = app_for(factory, monkeypatch)
    assert app.metric[0].value == "0"
    assert any("采集覆盖不足" in w.value for w in app.warning)
    assert any("尚未建立可处理的情报队列" in m.value for m in app.markdown)


def test_search_filters_review_and_audit_preserved(factory, monkeypatch):
    load_demo(factory)
    with factory() as s:
        before = s.scalar(select(func.count()).select_from(RawRevision))
    app = app_for(factory, monkeypatch)
    app.sidebar.radio[0].set_value("演示数据 Demo").run()
    app.sidebar.radio[1].set_value("Intelligence").run()
    next(w for w in app.text_input if w.label == "搜索情报").set_value("CATL").run()
    assert len([e for e in app.expander if e.label.startswith("#")]) == 1
    next(w for w in app.selectbox if w.label == "内容严重度").set_value("高").run()
    assert not [e for e in app.expander if e.label.startswith("#")]
    next(w for w in app.selectbox if w.label == "内容严重度").set_value("全部").run()
    next(w for w in app.text_input if w.label == "审核人").set_value("Synthetic UI QA")
    app.text_area[0].set_value("仅测试：原文和下一步均需核实")
    next(w for w in app.button if w.label == "保存审核记录").click().run()
    assert not app.exception
    with factory() as s:
        target = s.scalar(select(Event).where(Event.title.contains("CATL")))
        assert target.review_status == "confirmed" and target.lifecycle == "unknown"
        assert s.scalar(select(func.count()).select_from(ReviewLog)) == 1
        assert s.scalar(select(func.count()).select_from(RawRevision)) == before
        assert not s.scalars(select(Event).where(Event.data_mode == "live")).all()
    app.sidebar.radio[1].set_value("Overview").run()
    assert app.metric[0].value == "0"  # review cannot turn unknown into active


def test_upload_server_and_application_limit_are_both_five_mb(factory):
    config = tomllib.loads((ROOT / ".streamlit/config.toml").read_text(encoding="utf-8"))
    assert config["server"]["maxUploadSize"] == 5
    with pytest.raises(ValueError, match="5MB"):
        import_upload(factory, b"x" * 5_000_001, "demo")
    content = (ROOT / "fixtures/demo_shipments.csv").read_bytes()
    assert import_upload(factory, content, "demo")["inserted"] == 3
    assert import_upload(factory, content, "demo")["unchanged"] == 3
    with pytest.raises(ValueError):
        import_upload(factory, content, "live")
    with pytest.raises(UnicodeDecodeError):
        import_upload(factory, b"\xff", "demo")
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(ShipmentSnapshot)) == 3


def test_over_ten_thousand_rows_rolls_back(factory):
    header, row, *_ = (ROOT / "fixtures/demo_shipments.csv").read_text(encoding="utf-8").splitlines()
    content = (header + "\n" + (row + "\n") * 10_001).encode()
    assert len(content) < 5_000_000
    with pytest.raises(ValueError, match="10,000"):
        import_upload(factory, content, "demo")
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(ShipmentSnapshot)) == 0


def test_generic_capacity_label_is_not_battery_evidence_or_boosted():
    generic = make_view(
        event(title="Competitive European aviation capacity", event_type="行业产能"),
        payload={"title_zh": "电池行业产能动态｜Competitive European aviation capacity"},
        now=NOW,
    )
    assert generic.relevance_score == 1
    assert "相关性待核实" in generic.title
    assert "电池行业" not in generic.title
    assert generic.event.event_type == "行业产能"  # stored category and analysis unchanged


def test_malformed_port_metadata_cannot_become_current():
    assert not current_confirmed(event(port_signals_json="[]"), NOW)
