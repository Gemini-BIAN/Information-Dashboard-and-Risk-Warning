import csv
import io
from datetime import timedelta
from decimal import Decimal

import pytest
from openpyxl import Workbook
from sqlalchemy import func, select

from scm.platform.contracts import Record
from scm.platform.decision import attest_facts, cards, extract, handle, links, refresh, save_links
from scm.platform.decision_io import decision_report, import_links, source_health
from scm.platform.fuel import parse_workbook
from scm.platform.models import Audit, DecisionCard
from scm.platform.service import ingest, register
from scm.settings import utcnow


def rec(module="market", **patch):
    now = utcnow()
    raw = dict(
        external_id="DEMO-decision",
        module=module,
        title="DEMO diesel observation",
        body="Diesel prices reported in EUR. DEMO synthetic source only.",
        url="https://example.invalid/demo",
        published_at=now,
        fetched_at=now,
        mode="demo",
        verification="DEMO",
        country="DE",
    )
    return Record.model_validate({**raw, **patch})


def setup(session, record):
    register(
        session,
        [
            dict(
                id="decision-demo",
                name="DEMO synthetic",
                url="https://example.invalid/feed",
                adapter="fixture",
            )
        ],
    )
    return ingest(session, "decision-demo", record)[1]


def test_complete_decision_link_fact_handling_report_and_idempotence(factory):
    with factory.begin() as s:
        setup(s, rec())
        first = cards(s, "demo")[0]
        assert first["high_value"] and first["impact_level"] == "potential_unconfirmed"
        assert first["verified_facts"] == [] and first["facts"]
        assert not cards(s, "live") and not cards(s, "manual")
        count = s.scalar(select(func.count()).select_from(DecisionCard))
        assert refresh(s, "demo")["unchanged"] == 1
        assert s.scalar(select(func.count()).select_from(DecisionCard)) == count
        handle(s, first["card_id"], "demo", "in_progress", "tester", "DEMO review")
        attest_facts(
            s,
            first["card_id"],
            "demo",
            [f["quote"] for f in first["facts"]],
            "tester",
            "source checked in synthetic test",
        )
        assert cards(s, "demo")[0]["verified_facts"]
        report = decision_report(s, "demo", "weekly").html
        assert "候选行动" in report and "DEMO diesel" in report and first["sha256"] in report
        assert "DEMO diesel" not in decision_report(s, "live", "weekly").html
        handle(s, first["card_id"], "demo", "ignored", "tester", "not applicable")
        assert "DEMO diesel" not in decision_report(s, "demo", "weekly").html
        assert s.scalar(select(func.count()).select_from(Audit)) >= 3
        setup(
            s,
            rec(
                body="Diesel price revised. DEMO synthetic only.", fetched_at=utcnow() + timedelta(seconds=1)
            ),
        )
        latest = cards(s, "demo")[0]
        assert (
            latest["version"] == 2 and latest["handling_state"] == "pending" and not latest["verified_facts"]
        )
        with pytest.raises(ValueError):
            handle(s, first["card_id"], "demo", "resolved", "t", "obsolete")
        with pytest.raises(ValueError):
            handle(s, latest["card_id"], "live", "resolved", "t", "wrong namespace")


@pytest.mark.parametrize(
    "patch,expected",
    [
        ({"published_at": None}, "unknown"),
        ({"published_at": utcnow() - timedelta(days=40)}, "historical"),
        ({"published_at": utcnow() + timedelta(days=2)}, "future_publication"),
        ({"expires_at": utcnow() - timedelta(days=1)}, "expired"),
        ({"effective_at": utcnow() + timedelta(days=2)}, "not_yet_effective"),
        ({"published_at": None, "observed_at": utcnow() - timedelta(days=3)}, "recent_notice_unconfirmed"),
        ({"published_at": None, "observed_at": utcnow() + timedelta(days=1)}, "future_publication"),
    ],
)
def test_temporal_validity_no_date_guess(patch, expected):
    assert extract(rec(**patch).model_dump(mode="json"))["validity"] == expected


def test_uncertain_and_planned_claims_not_operating(factory):
    raw = rec(
        "capacity",
        title="DEMO battery plant",
        body="Battery plant expected to begin production in2028; it may be delayed. DEMO only.",
    ).model_dump(mode="json")
    event = extract(raw)
    assert "operating" not in [e["type"] for e in event["types"]]
    with factory.begin() as s:
        setup(s, rec("capacity", title="DEMO plan", body="The battery plant may be delayed. DEMO only."))
        c = cards(s, "demo")[0]
        assert not c["high_value"] and c["hypotheses"] and not c["verified_facts"]


def test_unknown_business_and_no_cross_country_matches(factory):
    with factory.begin() as s:
        setup(s, rec(country="FR"))
        save_links(
            s,
            "demo",
            [dict(link_id="DEMO-Germany", entity_type="cost_category", entity_id="diesel", country="DE")],
            "tester",
            "country filter",
        )
        c = cards(s, "demo")[0]
        assert c["business_relevance"] == "unknown" and c["impact_level"] == "unknown"
        assert all("延误天数" not in action for action in c["candidate_actions"])
        assert not links(s, "live") and not links(s, "manual")
        with pytest.raises(ValueError):
            attest_facts(s, c["card_id"], "demo", ["invented quote"], "tester", "bad")


@pytest.mark.parametrize(
    "entity_type,entity_id,patch",
    [
        (
            "port",
            "hamburg",
            dict(module="ports", title="DEMO Hamburg closure", body="Hamburg port is closed. DEMO only."),
        ),
        (
            "company",
            "CATL",
            dict(module="capacity", company="CATL", body="CATL invests in a new battery factory. DEMO only."),
        ),
        (
            "project",
            "DEMO-P1",
            dict(
                module="capacity",
                project_id="DEMO-P1",
                body="DEMO-P1 battery investment.",
                evidence_quote="DEMO-P1 battery investment.",
            ),
        ),
        ("route", "DEMO-route", dict(route="DEMO-route")),
        ("factory", "DEMO-factory", dict(factory="DEMO-factory")),
        ("transport", "DEMO-road", dict(transport="DEMO-road")),
    ],
)
def test_explicit_entity_links(factory, entity_type, entity_id, patch):
    with factory.begin() as s:
        setup(s, rec(**patch))
        save_links(
            s,
            "demo",
            [dict(link_id="DEMO-link", entity_type=entity_type, entity_id=entity_id)],
            "tester",
            "explicit match",
        )
        assert cards(s, "demo")[0]["user_context"][0]["entity_id"] == entity_id


def test_link_csv_excel_duplicates_atomic_and_namespace(factory):
    values = [dict(link_id="DEMO-csv", entity_type="port", entity_id="hamburg")]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(values[0]))
    writer.writeheader()
    writer.writerows(values)
    content = output.getvalue().encode("utf-8-sig")
    assert import_links(factory, content, "links.csv", "demo", "t", "test") == "updated"
    assert import_links(factory, content, "links.csv", "demo", "t", "test") == "unchanged"
    with pytest.raises(ValueError):
        import_links(factory, content, "links.csv", "live", "t", "wrong space")
    with factory.begin() as s:
        with pytest.raises(ValueError):
            save_links(s, "demo", values * 2, "t", "duplicate")
        assert len(links(s, "demo")) == 1
    w = Workbook()
    w.active.append(list(values[0]))
    w.active.append(list(values[0].values()))
    b = io.BytesIO()
    w.save(b)
    assert import_links(factory, b.getvalue(), "links.xlsx", "demo", "t", "xlsx") == "unchanged"
    w.active["B2"] = "=1+1"
    b = io.BytesIO()
    w.save(b)
    with pytest.raises(ValueError):
        import_links(factory, b.getvalue(), "links.xlsx", "demo", "t", "formula")


def workbook():
    w = Workbook()
    w.active.title = "Sheet1"
    w.active.append(["in EUR", "Euro-super", "Automotive gas oil diesel"])
    w.active.append([utcnow().replace(tzinfo=None), "1000 l", "1000 l"])
    for country in ["Germany", "France", "Belgium", "Netherlands"]:
        w.active.append([country, 1800, 2000])
    b = io.BytesIO()
    w.save(b)
    return b.getvalue()


def test_workbook_actual_cells_not_filename_and_conversion():
    values = parse_workbook(workbook(), "https://example.invalid/old-2024-file.xlsx", "INJECTED_TEST_CLIENT")
    assert len(values) == 4 and all(v.mode == "demo" for v in values)
    assert values[0].value == Decimal("2") and values[0].unit == "EUR/litre"
    assert values[0].published_at is None and values[0].observed_at.year == utcnow().year
    assert "Sheet1!C3" in values[0].body
    with pytest.raises(ValueError):
        parse_workbook(b"<html>error</html>", "https://example.invalid/file", "LIVE_HTTP")


def test_health_no_demo_rate_or_business_count(factory):
    with factory.begin() as s:
        setup(s, rec())
        health = source_health(s)
        assert all(h["live_attempts"] == 0 and h["observed_success_rate"] is None for h in health)


def test_schema_migration_roundtrip_preserves_evidence(tmp_path):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    from scm.database.session import make_engine, migrate
    from scm.settings import ROOT

    e = make_engine("sqlite:///" + str(tmp_path / "migration.db"))
    migrate(e)
    assert "decision_cards" in inspect(e).get_table_names()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    with e.begin() as connection:
        cfg.attributes["connection"] = connection
        command.downgrade(cfg, "004_platform")
    assert "decision_cards" not in inspect(e).get_table_names()
    assert "platform_evidence" in inspect(e).get_table_names()
    migrate(e)
    assert "decision_cards" in inspect(e).get_table_names()
    e.dispose()


def test_no_key_no_data_report_and_update_due_skip(factory, tmp_path, monkeypatch):
    from scm.platform import automation
    from scm.platform.models import PlatformSource
    from scm.platform.service import register
    from scm.settings import utcnow

    with factory.begin() as s:
        register(s)
        for row in s.scalars(select(PlatformSource)):
            row.last_checked_at = utcnow().isoformat()
        assert "本期无合格" in decision_report(s, "live").html
    calls = []
    monkeypatch.setattr(automation, "collect", lambda factory, sources: calls.append(sources) or [])
    result = automation.update(factory, tmp_path)
    assert calls == [[]] and not result["collection"]
    assert (tmp_path / "live-decision-weekly.html").read_text(encoding="utf-8").find("本期无合格") >= 0
