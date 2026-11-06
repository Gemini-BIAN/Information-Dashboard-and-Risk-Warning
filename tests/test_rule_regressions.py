"""Synthetic regression cases for Issue #3; never live-source validation."""

import json
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from scm.database.models import Event, RawRevision, ReviewLog, Source
from scm.intelligence.service import ingest, reassess_events, review
from scm.risk.lifecycle import RULE_VERSION, assess, port_signals
from scm.risk.policy import policy_state
from scm.risk.rules import PORT_ALIASES, port_risk
from scm.schemas import RawArticle
from scm.settings import utcnow


@pytest.mark.parametrize(
    "body,expected",
    [
        ("This regulation is repealed. It enters into force on 2020-01-01.", "废止"),
        ("本电池法规已废止。自2020年1月1日起实施。", "废止"),
        ("This is a proposal. Rules shall apply from 2020-01-01.", "提案"),
        ("This is a proposal. The previous regulation is in force.", "提案"),
        ("This is a proposal. It has entered into force.", "未知"),
        ("The regulation has entered into force. It expires on 2025-01-01.", "未知"),
        ("The regulation is not in force.", "未知"),
        ("The regulation was adopted. It shall apply from 2027-01-01.", "通过"),
        ("The regulation is in force. Effective from 2027-01-01.", "未知"),
        ("This regulation is repealed from 2027-01-01. It enters into force on 2020-01-01.", "未知"),
        ("Rules shall apply from 2020-01-01.", "未知"),
    ],
)
def test_policy_state_precedence_and_no_date_promotion(body, expected):
    result = policy_state("EU batteries regulation", body, today=date(2026, 11, 6))
    assert result["policy_status"] == expected
    assert result["policy_reasons"]


def test_independent_effective_expiry_repeal_dates():
    result = policy_state(
        "EU batteries regulation",
        "This regulation is repealed on 2025-02-03. Effective from 2020-01-01. It expires on 2024-12-31.",
        today=date(2026, 11, 6),
    )
    assert result["policy_status"] == "废止"
    assert result["effective_at"] == "2020-01-01"
    assert result["expiry_at"] == "2024-12-31"
    assert result["repeal_at"] == "2025-02-03"
    ambiguous = policy_state("Battery passport", "Effective from 2020-01-01. Effective from 2021-01-01.")
    assert ambiguous["effective_at"] is None
    assert any("多个不同日期" in r for r in ambiguous["policy_reasons"])


@pytest.mark.parametrize(
    "title,body,lifecycle,severity",
    [
        ("Rotterdam strike", "The strike has been cancelled.", "cancelled", "低"),
        ("Rotterdam strike", "The planned strike was called off.", "cancelled", "低"),
        ("Rotterdam strike", "The strike was withdrawn.", "cancelled", "低"),
        ("Rotterdam operations suspended", "Operations have resumed.", "resolved", "低"),
        ("Hamburg port closure", "The port has reopened.", "resolved", "低"),
        ("Rotterdam strike", "The strike is ongoing. The strike has been cancelled.", "unknown", "未知"),
        ("Rotterdam strike", "For example, a strike would close the port.", "unknown", "低"),
        ("Rotterdam strike", "If a strike occurred, operations would stop.", "unknown", "低"),
        ("Rotterdam strike", "In 2020 a strike began at Rotterdam.", "unknown", "低"),
        ("Rotterdam strike", "A strike began on 2020-01-01.", "unknown", "低"),
        ("Rotterdam strike", "The strike is ongoing.", "active", "高"),
        ("Rotterdam strike", "The strike is scheduled for next week.", "announced", "中"),
        ("Rotterdam strike", "This is a fictional simulation. Operations suspended.", "unknown", "未知"),
    ],
)
def test_lifecycle_negation_resolution_and_examples(title, body, lifecycle, severity):
    result = assess(title, body)
    assert result["lifecycle"] == lifecycle
    assert result["severity"] == severity
    assert result["reasons"]


def test_multi_port_document_scope():
    title = "Rotterdam and Hamburg operations update"
    signals = port_signals(
        title, "No strike in Rotterdam but Hamburg port is closed.", ["Rotterdam", "Hamburg"], PORT_ALIASES
    )
    assert signals["Rotterdam"]["lifecycle"] == "cancelled"
    assert signals["Hamburg"]["lifecycle"] == "active"
    assert signals["Hamburg"]["severity"] == "高"
    unnamed = port_signals(title, "Operations suspended.", ["Rotterdam", "Hamburg"], PORT_ALIASES)
    assert all(v["lifecycle"] == "unknown" for v in unnamed.values())


def add_event(session, body, url="https://official.test/item"):
    if session.get(Source, "regression") is None:
        session.add(
            Source(id="regression", name="Synthetic unit test", url="https://official.test", method="html")
        )
        session.flush()
    article = RawArticle(
        title="Rotterdam operations update",
        body=body,
        url=url,
        source="regression",
        published_at=utcnow() - timedelta(hours=1),
        fetched_at=utcnow(),
        data_mode="live",
    )
    return ingest(session, article)[1]


@pytest.mark.parametrize(
    "body",
    [
        "The strike has been cancelled.",
        "Operations have resumed.",
        "The strike is ongoing. The strike has been cancelled.",
        "A strike may affect operations. This is a hypothetical scenario.",
        "Rotterdam tariff update.",
    ],
)
def test_resolved_unclear_non_operational_items_do_not_raise_current_port(factory, body):
    with factory.begin() as s:
        event = add_event(s, body)
        level, reasons, active = port_risk(s, "Rotterdam", "live")
        assert level == "未知" and not active
        assert any("未知" in r for r in reasons)
        assert event.rule_version == RULE_VERSION and event.source_confidence == "unreviewed_public"
        assert s.scalar(select(func.count()).select_from(RawRevision)) == 1


def test_announced_vs_active_and_namespace_protection(factory):
    with factory.begin() as s:
        event = add_event(s, "Rotterdam strike is planned.")
        assert port_risk(s, "Rotterdam", "live")[0] == "中"
        event = add_event(s, "Rotterdam operations suspended.")
        assert port_risk(s, "Rotterdam", "live")[0] == "高"
        assert port_risk(s, "Rotterdam", "demo")[0] == "未知"
        review(s, event.id, "rejected", "planner", "Superseded")
        assert port_risk(s, "Rotterdam", "live")[0] == "未知"


def test_reassessment_idempotent_and_auditable(factory):
    with factory.begin() as s:
        event = add_event(s, "Rotterdam strike was cancelled.")
        review(s, event.id, "confirmed", "planner", "Old version reviewed")
        event.rule_version, event.risk_level = "legacy", "高"
        event.port_signals_json = "{}"
        raw_count = s.scalar(select(func.count()).select_from(RawRevision))
        assert reassess_events(s) == 1
        assert event.review_status == "pending" and event.lifecycle == "cancelled"
        assert event.risk_level == "低" and event.rule_version == RULE_VERSION
        assert reassess_events(s) == 0
        assert s.scalar(select(func.count()).select_from(RawRevision)) == raw_count
        audit = s.scalar(select(ReviewLog).where(ReviewLog.action == "rule_reassessment"))
        assert audit and "legacy" in audit.reason
        assert port_risk(s, "Rotterdam", "live")[0] == "未知"
        assert json.loads(event.lifecycle_reasons_json)


def test_negated_body_and_unrelated_cancellation_do_not_override_actual_state():
    result = assess("Rotterdam operations suspended", "Operations are not suspended.")
    assert result["lifecycle"] == "unknown" and result["severity"] == "低"
    result = assess(
        "Rotterdam operations suspended", "An unrelated meeting was cancelled. Operations are suspended."
    )
    assert result["lifecycle"] == "active" and result["severity"] == "高"
    assert assess("Rotterdam strike", "The strike is not cancelled.")["lifecycle"] == "unknown"


def test_proposal_historical_effective_clause_stays_proposal():
    result = policy_state("Proposal for batteries regulation", "It enters into force on 2020-01-01.")
    assert result["policy_status"] == "提案"
    assert result["effective_at"] == "2020-01-01"


def test_legacy_signal_not_used_for_current_port_before_reassessment(factory):
    with factory.begin() as s:
        event = add_event(s, "Rotterdam operations suspended.")
        assert port_risk(s, "Rotterdam", "live")[0] == "高"
        event.rule_version = "legacy"
        assert port_risk(s, "Rotterdam", "live")[0] == "未知"
        assert reassess_events(s) == 1
        audit = s.scalar(select(ReviewLog).where(ReviewLog.action == "rule_reassessment"))
        payload = json.loads(audit.reason)
        assert payload["before"]["rule_version"] == "legacy"
        assert payload["after"]["rule_version"] == RULE_VERSION


def test_terminal_headline_cannot_be_lost_to_positive_body_background():
    result = assess("Rotterdam strike cancelled", "The strike is ongoing.")
    assert result["lifecycle"] == "unknown" and result["severity"] == "未知"
    assert assess("Rotterdam strike", "The strike has been cancelled.")["lifecycle"] == "cancelled"


def test_actual_001_database_upgrade_preserves_evidence_and_reassesses(tmp_path):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from scm.database.session import make_engine, migrate
    from scm.settings import ROOT

    engine = make_engine("sqlite:///" + str(tmp_path / "legacy.db"))
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "001")
        connection.execute(
            text(
                "INSERT INTO sources (id,name,url,method,enabled,last_status,audit_json) VALUES ('legacy','Synthetic legacy','https://official.test','html',1,'NOT TESTED','{}')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO events (id,canonical_url,title,source_id,published_at,fetched_at,updated_at,data_mode,content_hash,event_type,countries_json,ports_json,policy_status,risk_level,risk_reasons_json,review_status,topic) VALUES (1,'https://official.test/legacy','Rotterdam strike','legacy',:stamp,:stamp,:stamp,'live','legacyhash','港口运营','[]','[\"Rotterdam\"]','未知','高','[]','confirmed','港口运营:Rotterdam')"
            ),
            {"stamp": utcnow().isoformat()},
        )
        connection.execute(
            text(
                "INSERT INTO raw_revisions (event_id,title,body,source_url,published_at,fetched_at,content_hash) VALUES (1,'Rotterdam strike','The strike was cancelled.','https://official.test/legacy',:stamp,:stamp,'legacyhash')"
            ),
            {"stamp": utcnow().isoformat()},
        )
    migrate(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as s:
        assert s.get(Event, 1).rule_version == "legacy"
        assert port_risk(s, "Rotterdam", "live")[0] == "未知"
        assert reassess_events(s) == 1
        assert s.get(Event, 1).lifecycle == "cancelled"
        assert s.get(Event, 1).review_status == "pending"
        assert (
            s.scalar(select(func.count()).select_from(RawRevision)) == 2
        )  # new content-hash format, old revision retained
        assert s.scalar(select(func.count()).select_from(ReviewLog)) == 1
    migrate(engine)
    engine.dispose()
