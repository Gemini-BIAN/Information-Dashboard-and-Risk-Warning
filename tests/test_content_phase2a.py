"""Synthetic HTTP/DB regressions; never counted as real-source acceptance."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select

from scm.collectors.http import SafeFetcher
from scm.collectors.parsers import parse_article
from scm.content.digest import generate_digest
from scm.content.relevance import relevance
from scm.content.service import collect_content
from scm.database.models import Analysis, Event, RawRevision, Source

NOW = datetime(2026, 11, 9, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    "title,body,decision,reason",
    [
        ("Airbus adds aviation capacity", "New aircraft production lines.", "excluded", "GENERIC_AVIATION"),
        ("China tariffs on domestic goods", "China domestic tariffs only.", "excluded", "UNRELATED_TARIFF"),
        ("Product safety notice", "Unrelated toaster recall.", "excluded", "NO_BUSINESS_LINK"),
        (
            "Hamburg port omission",
            "An explicit port omission on the Europe service.",
            "relevant",
            "EXPLICIT_CARRIER_CHANGE",
        ),
        ("ADR revisions", "ADR dangerous goods rules revised.", "relevant", "DG_RULE"),
        ("Europe electrolyte plant", "Electrolyte factory production update.", "relevant", "BATTERY_PLANT"),
        ("Battery factory update", "Battery plant expansion in Europe.", "relevant", "BATTERY_PLANT"),
        ("EU customs rules", "European Union customs changes.", "relevant", "EU_TRADE"),
        ("EU battery regulation", "Battery passport rules.", "relevant", "BATTERY_POLICY"),
    ],
)
def test_business_filter(title, body, decision, reason):
    _, _, result = relevance(title, body, NOW - timedelta(hours=1), NOW)
    assert result.decision == decision and reason in result.reason_codes


@pytest.mark.parametrize(
    "age,lifecycle,code", [(1, "resolved", "RESOLVED_OR_CANCELLED"), (60, "active", "HISTORICAL_ONLY")]
)
def test_old_resolved_strikes_not_priority(age, lifecycle, code):
    _, _, result = relevance(
        "Hamburg port strike",
        "A strike affected terminal operations.",
        NOW - timedelta(days=age),
        NOW,
        lifecycle,
    )
    assert result.decision != "relevant"
    assert code in result.reason_codes


def test_unknown_future_and_old_effective_dates_do_not_make_current():
    for pub, code in [
        (None, "UNKNOWN_PUBLICATION"),
        (NOW + timedelta(days=1), "FUTURE_PUBLICATION"),
        (NOW - timedelta(days=400), "HISTORICAL_ONLY"),
    ]:
        _, _, rel = relevance("Battery regulation", "Battery rules effective 2020-01-01.", pub, NOW)
        assert rel.decision != "relevant" and code in rel.reason_codes


def hamburg_html(title="Hamburg port omission", date="09 Nov 2026 11:00"):
    return f'<html><div id="content"><h1>{title}</h1><p>{date}</p><div id="body"><p>Hamburg port omission has been announced for a Europe service. Specific voyage applicability requires confirmation by the shipping line before planning changes.</p></div><aside>CONTACT SECRET</aside></div></html>'


def test_hamburg_scope_date_and_shell_guard():
    p = parse_article(hamburg_html(), "https://official.test/news/1", "hamburg")
    assert p["published_at"] == datetime(2026, 11, 9, 10, tzinfo=UTC)
    assert "CONTACT SECRET" not in p["body"]
    assert (
        parse_article(hamburg_html(date="unknown"), "https://official.test/news/1", "hamburg")["published_at"]
        is None
    )
    with pytest.raises(ValueError):
        parse_article("<h1>Listing</h1>", "https://official.test/news", "hamburg")


def spec(id="test-source"):
    return {
        "id": id,
        "name": "Synthetic official source",
        "url": "https://official.test/news",
        "method": "html",
        "parser": "hamburg",
        "article_pattern": "/news/",
        "limit": 3,
        "use_canonical": True,
        "reuse_policy": {
            "permission": "allowed_full_text",
            "status": "reviewed_allowed",
            "verified_at": NOW.isoformat(),
            "license": "synthetic only",
            "notice_url": "https://official.test/legal",
            "evidence_ref": "synthetic",
        },
    }


def test_permissions_fail_before_network_and_source_isolation(factory):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.url.path == "/news":
            return httpx.Response(200, text='<main><a href="/news/1">Sample</a></main>')
        return httpx.Response(200, text=hamburg_html())

    bad = spec("restricted-source")
    bad["reuse_policy"]["permission"] = "unknown"
    f = SafeFetcher(httpx.Client(transport=httpx.MockTransport(handler)), interval=0, retries=0)
    results = collect_content(factory, [bad, spec()], f, now=NOW)
    assert results[0]["failure_stage"] == "permission"
    assert results[1]["writes"] == {"inserted": 1}
    assert len(seen) == 3
    with factory() as session:
        assert session.scalar(select(func.count(Source.id))) == 1
        assert session.scalar(select(Source)).url == spec()["url"]
        event = session.scalar(select(Event))
        original = (event.risk_level, event.lifecycle, event.rule_version)
        analysis = session.scalar(select(Analysis))
        record = json.loads(analysis.payload_json)["content_v1"]
        assert record["business_relevance"]["decision"] == "relevant"
        assert record["operational_state"] == "unknown"
        assert record["applicability"] is None
        assert original == (event.risk_level, event.lifecycle, event.rule_version)
        assert analysis.provider == "rules-only"
        document, meta = generate_digest(session, NOW.date(), now=NOW)
        assert meta["selected"] == 1 and "原文" in document and "覆盖不足" in document
    again = collect_content(factory, [spec()], f, now=NOW)
    assert again[0]["writes"] == {"unchanged": 1}
    assert again[0]["content_assessments_written"] == 0
    with factory() as session:
        assert session.scalar(select(func.count(Event.id))) == 1
        assert session.scalar(select(func.count(RawRevision.id))) == 1
        assert session.scalar(select(func.count(Analysis.id))) == 1
        document, meta = generate_digest(
            session, (NOW + timedelta(days=1)).date(), now=NOW + timedelta(days=1)
        )
        assert meta["selected"] == 0 and "不" in document
        document, meta = generate_digest(session, NOW.date(), mode="demo", now=NOW)
        assert meta["selected"] == 0 and "Hamburg port omission" not in document
    f.close()


def test_assessment_failure_isolated_and_next_source_runs(factory, monkeypatch):
    import scm.content.service as service

    seen = []

    def fake_run(factory, specs, **kwargs):
        seen.append(specs[0]["id"])
        return [{"source": specs[0]["id"], "status": "PASS", "writes": {}}]

    def fail_once(session, selected, now):
        if selected["id"] == "broken-source":
            raise ValueError("synthetic assessment failure")
        return 0

    monkeypatch.setattr(service, "run_collection", fake_run)
    monkeypatch.setattr(service, "attach_content", fail_once)
    results = collect_content(factory, [spec("broken-source"), spec("good-source")], now=NOW)
    assert seen == ["broken-source", "good-source"]
    assert results[0]["failure_stage"] == "content_assessment"
    assert results[1]["status"] == "PASS"


@pytest.mark.parametrize("permission", ["unknown", "metadata_only", "link_only", "blocked"])
def test_non_text_permissions_fail_closed(factory, permission):
    chosen = spec()
    chosen["reuse_policy"]["permission"] = permission
    result = collect_content(factory, [chosen], now=NOW)
    assert result[0]["failure_stage"] == "permission"
    with factory() as session:
        assert session.scalar(select(func.count(Event.id))) == 0


def test_revision_update_preserves_previous_reference_and_canonical(factory):
    state = {"title": "Hamburg port omission"}

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.url.path == "/news":
            return httpx.Response(200, text='<main><a href="/news/alias">Synthetic</a></main>')
        return httpx.Response(
            200,
            text='<link rel="canonical" href="https://official.test/news/stable">'
            + hamburg_html(state["title"]),
        )

    f = SafeFetcher(httpx.Client(transport=httpx.MockTransport(handler)), interval=0, retries=0)
    collect_content(factory, [spec()], f, now=NOW)
    state["title"] = "Hamburg port omission — updated sailing"
    result = collect_content(factory, [spec()], f, now=NOW)
    assert result[0]["writes"] == {"updated": 1}
    with factory() as session:
        assert session.scalar(select(func.count(Event.id))) == 1
        event = session.scalar(select(Event))
        assert event.canonical_url == "https://official.test/news/stable"
        latest = session.scalar(select(Analysis).order_by(Analysis.id.desc()))
        record = json.loads(latest.payload_json)["content_v1"]
        assert record["update_version"] == 2 and record["previous_record_ref"].endswith("revision-1")
    f.close()


def test_non_operational_background_excluded():
    for title in [
        "Port evening reception in Prague",
        "Annual meeting at the port",
        "Direct Air Capture center in the port",
    ]:
        _, _, result = relevance(title, "Generic technology and networking news.", NOW, NOW)
        assert result.decision == "excluded" and "NON_OPERATIONAL_BACKGROUND" in result.reason_codes
