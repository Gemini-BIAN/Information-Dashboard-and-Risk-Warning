import json
from datetime import date, timedelta

import pytest
from sqlalchemy import func, inspect, select

from scm.collectors.service import load_demo
from scm.database.models import (
    Analysis,
    Event,
    RawRevision,
    Report,
    ReviewLog,
    ShipmentSnapshot,
    Source,
)
from scm.database.session import migrate
from scm.exports import safe_csv
from scm.intelligence.service import canonical_url, ingest, override_port, review
from scm.reports.service import generate_report, period_bounds
from scm.risk.rules import classify, grade, port_risk
from scm.scheduler import scheduled_reports
from scm.schemas import RawArticle
from scm.settings import ROOT, utcnow
from scm.shipments.service import import_csv, shipment_risks


def sample(**kwargs):
    values = dict(
        title="Rotterdam operations suspended",
        body="Rotterdam operations suspended after a safety incident. Official details must be checked before updating shipment plans.",
        url="https://official.test/news/1",
        source="test",
        fetched_at=utcnow(),
        published_at=utcnow() - timedelta(hours=1),
        data_mode="live",
    )
    values.update(kwargs)
    return RawArticle(**values)


def source(session):
    session.add(Source(id="test", name="Test official", url="https://official.test", method="html"))
    session.flush()


def test_migration_and_repeatability(factory):
    with factory() as s:
        engine = s.get_bind()
        migrate(engine)
        assert set(["events", "raw_revisions", "shipment_snapshots", "reports"]).issubset(
            inspect(engine).get_table_names()
        )
        assert len(inspect(engine).get_foreign_keys("analyses")) == 2


def test_fixture_end_to_end_and_idempotence(factory, monkeypatch):
    monkeypatch.delenv("SCM_LLM_API_KEY", raising=False)
    monkeypatch.setenv("SCM_LLM_PROVIDER", "none")
    assert load_demo(factory) == {"inserted": 5}
    assert load_demo(factory) == {"unchanged": 5}
    with factory() as s:
        events = s.scalars(select(Event)).all()
        assert len(events) == 5
        assert all(e.canonical_url and e.source_id and e.data_mode == "demo" for e in events)
        assert s.scalar(select(func.count()).select_from(Analysis)) == 5
        high = [e for e in events if e.risk_level == "高"]
        assert high and all(json.loads(e.risk_reasons_json) for e in high)
        assert not s.scalars(select(Event).where(Event.data_mode == "live")).all()


def test_canonical_and_content_dedupe(factory):
    published = utcnow()
    with factory.begin() as s:
        source(s)
        status, first = ingest(
            s, sample(url="https://OFFICIAL.test/news/1/?utm_source=x#tag", published_at=published)
        )
        status2, second = ingest(s, sample(url="https://official.test/news/1", published_at=published))
        status3, third = ingest(s, sample(url="https://official.test/news/alias", published_at=published))
        assert status == "inserted" and status2 == status3 == "unchanged"
        assert first.id == second.id == third.id
    assert canonical_url("https://a.test/x?b=2&a=1&utm_campaign=c#z") == "https://a.test/x?a=1&b=2"


def test_update_preserves_raw_and_resets_review(factory):
    with factory.begin() as s:
        source(s)
        _, event = ingest(s, sample())
        review(s, event.id, "confirmed", "planner", "Checked")
        assert event.review_status == "confirmed"
        status, updated = ingest(
            s,
            sample(
                body="Rotterdam operations resumed following safety checks. This official update supersedes the previous announcement."
            ),
        )
        assert status == "updated" and updated.id == event.id
        assert event.review_status == "pending"
        assert s.scalar(select(func.count()).select_from(RawRevision)) == 2
        assert s.scalar(select(func.count()).select_from(ReviewLog)) == 1


@pytest.mark.parametrize(
    "title, expected",
    [
        ("Rotterdam strike", "高"),
        ("Rotterdam possible strike", "中"),
        ("Rotterdam no strike", "低"),
        ("Rotterdam strike ended", "低"),
        ("Hamburg port omission", "中"),
        ("CATL capacity update", "低"),
    ],
)
def test_explainable_rules(title, expected):
    level, reasons = grade(title, "", classify(title, "")["event_type"])
    assert level == expected and reasons


@pytest.mark.parametrize(
    "text, expected",
    [
        ("EU battery passport proposal", "提案"),
        ("EU batteries regulation has adopted rules", "通过"),
        ("EU batteries regulation has entered into force", "实施"),
        ("EU batteries regulation is repealed", "废止"),
        ("EU battery passport news", "未知"),
    ],
)
def test_policy_states(text, expected):
    assert classify(text, "")["policy_status"] == expected


def test_port_override_audit_expiry_and_demo_isolation(factory):
    load_demo(factory)
    with factory.begin() as s:
        level, _, _ = port_risk(s, "Rotterdam", "live")
        assert level == "未知"
        override_port(
            s, "Rotterdam", "live", "中", "planner", "Carrier call pending", utcnow() + timedelta(hours=2)
        )
        s.flush()
        assert port_risk(s, "Rotterdam", "live")[0] == "中"
        assert port_risk(s, "Rotterdam", "live", utcnow() + timedelta(hours=3))[0] == "未知"
        assert s.scalar(select(func.count()).select_from(ReviewLog)) == 1
        with pytest.raises(ValueError):
            override_port(s, "Rotterdam", "live", "高", "planner", "", utcnow() + timedelta(hours=2))


def test_stale_unknown_and_rejected_port_events_excluded(factory):
    with factory.begin() as s:
        source(s)
        _, event = ingest(s, sample(published_at=utcnow() - timedelta(days=40)))
        assert port_risk(s, "Rotterdam", "live")[0] == "未知"
        ingest(
            s,
            sample(
                published_at=None,
                body="Rotterdam strike. This advisory has unknown publication date and must be checked before use.",
            ),
        )
        assert port_risk(s, "Rotterdam", "live")[0] == "未知"
        ingest(s, sample(published_at=utcnow()))
        assert port_risk(s, "Rotterdam", "live")[0] == "高"
        review(s, event.id, "rejected", "user", "Superseded")
        assert port_risk(s, "Rotterdam", "live")[0] == "未知"


def test_review_notes_and_validation(factory):
    with factory.begin() as s:
        source(s)
        _, event = ingest(s, sample())
        review(s, event.id, "note", "planner", "Need confirmation")
        assert event.review_status == "pending"
        with pytest.raises(ValueError):
            review(s, event.id, "confirmed", "", "test")


def test_shipment_snapshots_delta_idempotency_and_arrival(factory):
    text = (ROOT / "fixtures/demo_shipments.csv").read_text()
    with factory.begin() as s:
        assert import_csv(s, text, "demo")["inserted"] == 3
        assert import_csv(s, text, "demo")["unchanged"] == 3
        risks = shipment_risks(s, "demo")
        first = next(r for r in risks if r["container_number"] == "DEMO-0001")
        assert first["previous_delta_hours"] == first["baseline_delta_hours"] == 72
        assert first["risk_level"] == "高"
        second = next(r for r in risks if r["container_number"] == "DEMO-0002")
        assert second["previous_delta_hours"] is None and second["risk_level"] == "未知"
        assert shipment_risks(s, "live") == []
        current = s.scalar(
            select(ShipmentSnapshot)
            .where(ShipmentSnapshot.container_number == "DEMO-0001")
            .order_by(ShipmentSnapshot.updated_at.desc())
        )
        current.ata = current.eta
        s.flush()
        assert (
            next(r for r in shipment_risks(s, "demo") if r["container_number"] == "DEMO-0001")["risk_level"]
            == "低"
        )


def test_out_of_order_snapshots_and_port_isolation(factory):
    text = (ROOT / "fixtures/demo_shipments.csv").read_text()
    lines = text.splitlines()
    with factory.begin() as s:
        import_csv(s, "\n".join([lines[0], lines[2], lines[1], lines[3]]), "demo")
        risks = shipment_risks(s, "demo")
        assert next(r for r in risks if r["container_number"] == "DEMO-0001")["previous_delta_hours"] == 72
        # Same container/voyage, different port call: cannot compare ETA across ports.
        import_csv(s, "\n".join([lines[0], lines[2].replace("Rotterdam", "Hamburg")]), "demo")
        assert len(shipment_risks(s, "demo")) == 3


def test_csv_invalid_and_conflict_atomicity(factory):
    text = (ROOT / "fixtures/demo_shipments.csv").read_text()
    with factory.begin() as s:
        with pytest.raises(ValueError):
            import_csv(s, text.replace("T08:00:00Z", "T08:00:00"), "demo")
        assert s.scalar(select(func.count()).select_from(ShipmentSnapshot)) == 0
        with pytest.raises(ValueError):
            import_csv(s, text, "live")
        import_csv(s, text, "demo")
        with pytest.raises(ValueError, match="Conflicting snapshot"):
            import_csv(s, text.replace("2026-11-23T08:00:00Z", "2026-11-24T08:00:00Z"), "demo")


def test_port_association_is_tentative(factory):
    load_demo(factory)
    with factory.begin() as s:
        import_csv(s, (ROOT / "fixtures/demo_shipments.csv").read_text(), "demo")
        first = next(r for r in shipment_risks(s, "demo") if r["container_number"] == "DEMO-0001")
        assert first["linked_events"] and "待核实" in first["linked_events"][0]["association"]
        assert any("不构成" in r for r in first["reasons"])
        assert shipment_risks(s, "live") == []


def test_reports_html_history_empty_weekly_grouping_and_escaping(factory):
    load_demo(factory)
    with factory.begin() as s:
        daily = generate_report(s, "daily", "demo", date(2026, 11, 6))
        weekly = generate_report(s, "weekly", "demo", date(2026, 11, 6))
        assert "演示数据 / 非真实新闻" in daily.html and "原文证据" in daily.html
        assert "未来1–3个月" in weekly.html and "example.invalid" in weekly.html
        assert generate_report(s, "daily", "demo", date(2026, 11, 6)).id == daily.id
        live = generate_report(s, "daily", "live", date(2026, 11, 6))
        assert "本期没有重要新增事件" in live.html and "example.invalid" not in live.html
        assert s.scalar(select(func.count()).select_from(Report)) == 3
        source(s)
        _, event = ingest(s, sample(title="<script>alert(1)</script> Rotterdam strike"))
        document = generate_report(s, "daily", "live").html
        assert "<script>alert(1)</script>" not in document and "&lt;script&gt;" in document
        review(s, event.id, "rejected", "user", "Not valid")
        assert "official.test/news/1" not in generate_report(s, "daily", "live").html


def test_reporting_timezone_and_scheduler_job(factory):
    start, end = period_bounds("daily", date(2026, 11, 6))
    assert start.isoformat() == "2026-11-05T16:00:00+00:00"
    assert (end - start).total_seconds() == 86400
    assert scheduled_reports(factory, "weekly", date(2026, 11, 1)) > 0
    with factory() as s:
        report = s.scalar(select(Report))
        assert report.period_start == "2026-10-25T16:00:00+00:00"


def test_formula_safe_export():
    exported = safe_csv([{"title": '=HYPERLINK("evil")', "mode": "demo"}])
    assert "'=HYPERLINK" in exported and "demo" in exported


def test_explicit_effective_dates_and_future_status():
    result = classify("EU battery passport", "Rules shall apply from 18 February 2027.")
    assert result["effective_at"] == "2027-02-18"
    assert result["policy_status"] == "未知"
    result = classify("EU batteries regulation", "Rules enter into force on 2025-01-01.")
    assert result["effective_at"] is None  # only configured explicit grammar is accepted
    result = classify("EU batteries regulation", "This regulation enters into force on 2025-01-01.")
    assert result["effective_at"] == "2025-01-01" and result["policy_status"] == "实施"


def test_publication_metadata_updates_create_raw_revision(factory):
    now = utcnow()
    with factory.begin() as s:
        source(s)
        _, event = ingest(s, sample(published_at=None))
        status, _ = ingest(s, sample(published_at=now))
        assert status == "updated"
        revisions = s.scalars(select(RawRevision).where(RawRevision.event_id == event.id)).all()
        assert len(revisions) == 2 and {r.published_at for r in revisions} == {None, now.isoformat()}
