"""Synthetic regression inputs are DEMO/Manual; real HTTP acceptance is documented separately."""

import json
from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from scm.platform.adapters import permission_gate
from scm.platform.contracts import Record
from scm.platform.decision import cards, refresh
from scm.platform.decision_io import decision_report
from scm.platform.diesel_import import load, series
from scm.platform.entities import operations, projects
from scm.platform.models import Evidence, Item
from scm.platform.service import ingest, register
from scm.ports.detail import detail
from scm.settings import utcnow


def record(**patch):
    now = utcnow()
    raw = dict(
        external_id="DEMO-pin-activate",
        module="ports",
        title="DEMO Rotterdam pilot restriction",
        body="DEMO synthetic only. Rotterdam pilot service restriction is active.",
        url="https://example.invalid/pin-activate",
        published_at=now,
        fetched_at=now,
        mode="demo",
        verification="DEMO",
        operational_event_id="DEMO-pilot-cycle1",
        operational_status="active",
        status_at=now,
        event_scope="channel",
        field_evidence={"operational_status": "Rotterdam pilot service restriction is active."},
    )
    return Record.model_validate({**raw, **patch})


def store(s, r):
    register(
        s,
        [
            dict(
                id="phase4-demo", name="DEMO synthetic", url="https://example.invalid/feed", adapter="fixture"
            )
        ],
    )
    return ingest(s, "phase4-demo", r)


def test_activate_deactivate_one_entity_cards_report_details(factory):
    now = utcnow()
    with factory.begin() as s:
        store(s, record(status_at=now - timedelta(hours=1)))
        assert operations(s, "demo", now)[0]["state"] == "active"
        assert cards(s, "demo", True)[0]["high_value"]
        body = "DEMO synthetic only. Rotterdam pilot service restriction is resolved."
        resolved = record(
            external_id="DEMO-pin-deactivate",
            title="DEMO Rotterdam service restored",
            url="https://example.invalid/pin-deactivate",
            body=body,
            operational_status="resolved",
            status_at=now,
            field_evidence={"operational_status": body},
        )
        store(s, resolved)
        assert len(operations(s, "demo", now)) == 1
        assert operations(s, "demo", now)[0]["state"] == "resolved"
        assert not cards(s, "demo", True)
        assert sum(c["entity_representative"] for c in cards(s, "demo")) == 1
        assert "DEMO Rotterdam pilot restriction" not in decision_report(s, "demo").html
        d = detail(s, "rotterdam", "demo")
        assert len(d["records"]) == 2
        assert all(r["state"] == "resolved" for r in d["records"])
        assert d["snapshot"]["state"] == "unknown"  # Restoration is not all-port normal.
        count = s.scalar(select(func.count()).select_from(Evidence))
        assert store(s, resolved)[0] == "unchanged"
        assert refresh(s, "demo")["unchanged"] == 2
        assert count == s.scalar(select(func.count()).select_from(Evidence))
        assert not operations(s, "live") and not cards(s, "manual")


@pytest.mark.parametrize("state", ["cancelled", "expired", "resolved", "scheduled", "unknown"])
def test_nonactive_lifecycle_never_current_risk(factory, state):
    with factory.begin() as s:
        store(s, record(operational_status=state))
        assert operations(s, "demo")[0]["state"] == state
        if state != "scheduled":
            assert not cards(s, "demo", True)


def test_expiry_stale_conflict_and_out_of_order_publication(factory):
    now = utcnow()
    with factory.begin() as s:
        store(s, record(status_at=now - timedelta(days=3)))
        assert operations(s, "demo", now)[0]["state"] == "unknown"
        store(
            s,
            record(
                external_id="DEMO-pin-expire",
                effective_at=now - timedelta(hours=2),
                expires_at=now - timedelta(hours=1),
                status_at=now - timedelta(hours=2),
            ),
        )
        assert operations(s, "demo", now)[0]["state"] == "expired"
        store(
            s,
            record(
                external_id="DEMO-pin-restored",
                operational_status="resolved",
                status_at=now - timedelta(hours=2),
            ),
        )
        assert operations(s, "demo", now)[0]["conflict"]
        assert operations(s, "demo", now)[0]["state"] == "unknown"


def project(**patch):
    body = (
        "DEMO AESC new factory approved. Planned capacity 15.8 GWh/year. Trial production is not full output."
    )
    return record(
        **{
            **dict(
                module="capacity",
                operational_event_id=None,
                operational_status="unknown",
                status_at=None,
                event_scope="unknown",
                body=body,
                company="aesc",
                project_id="DEMO-sunderland",
                factory="DEMO-plant2",
                country="GB",
                location="Sunderland",
                product="EV batteries",
                project_status="approved",
                capacity="15.8",
                capacity_unit="GWh/year",
                capacity_basis="planned",
                evidence_quote=body,
                field_evidence={
                    "capacity": "Planned capacity 15.8 GWh/year.",
                    "project_status": "DEMO AESC new factory approved.",
                },
            ),
            **patch,
        }
    )


def test_project_history_one_factory_units_plan_actual_and_conflicts(factory):
    with factory.begin() as s:
        r = project()
        store(s, r)
        store(
            s, r.model_copy(update={"external_id": "DEMO-plant-trial", "project_status": "trial_production"})
        )
        values = projects(s, "demo")
        assert len(values) == 1 and len(values[0]["timeline"]) == 2
        assert values[0]["current"]["raw"]["actual_start"] is None
        assert values[0]["announced_at"] is None
        assert values[0]["capacity_value"] == "15.8" and values[0]["capacity_basis"] == "planned"
        assert values[0]["capacity_claims"][0]["basis"] == "planned"
        assert values[0]["current"]["raw"]["project_status"] == "trial_production"
        other = r.model_copy(
            update={
                "external_id": "DEMO-conflict",
                "capacity_unit": "tonnes/year",
                "location": "Different town",
            }
        )
        store(s, other)
        assert set(projects(s, "demo")[0]["conflicts"]) == {"capacity", "location", "project_status"}
        assert not cards(s, "demo", True)
        assert not projects(s, "live")
        assert s.scalar(select(func.count()).select_from(Item)) == 3


def test_field_specific_evidence_and_plan_dates():
    with pytest.raises(ValidationError):
        project(actual_start="2025-12-16")
    with pytest.raises(ValidationError):
        record(field_evidence={})
    with pytest.raises(ValidationError):
        project(
            capacity_basis="nameplate", field_evidence={"project_status": "DEMO AESC new factory approved."}
        )


def diesel(day="2026-11-02", **patch):
    return {
        **dict(
            origin_source_id="ec-weekly-fuel",
            source_url="https://energy.ec.europa.eu/data",
            country="Germany",
            observed_date=day,
            value="2000",
            currency="EUR",
            unit="EUR/1000l",
            fetched_at=utcnow().isoformat(),
            method="existing-user-tool",
        ),
        **patch,
    }


def test_diesel_history_dedup_conflicts_and_exact_week(factory):
    raw = json.dumps([diesel(), diesel("2026-11-09", value="2100")]).encode()
    assert load(factory, raw, "prices.json", "tester", "synthetic manual test")["inserted"] == 2
    assert load(factory, raw, "prices.json", "tester", "repeat")["unchanged"] == 2
    with factory() as s:
        data = series(s, "manual", "ec-weekly-fuel", "DE", "EUR", "EUR/litre")
        assert data[0]["weekly_change_pct"] is None
        assert data[1]["weekly_change_pct"] == "5.00"
    conflict = json.dumps([diesel(value="9999")]).encode()
    assert load(factory, conflict, "prices.json", "tester", "conflict")["conflicts"] == 1
    with factory() as s:
        assert len(series(s, "manual", "ec-weekly-fuel", "DE", "EUR", "EUR/litre")) == 2
        assert not series(s, "live", "ec-weekly-fuel", "DE", "EUR", "EUR/litre")
    with pytest.raises(ValidationError):
        load(factory, json.dumps([diesel(), diesel(value="NaN")]).encode(), "p.json", "t", "invalid")


def test_restricted_sources_stay_zero_request():
    from scm.collectors.http import AccessBlocked
    from scm.platform.service import specs

    for spec in specs():
        if spec["id"] in ["catl", "maersk"] or "rotterdam" in spec["id"]:
            with pytest.raises(AccessBlocked):
                permission_gate(spec, utcnow())


def test_manual_link_summary_atomic_and_not_live(factory):
    from scm.platform.manual_metadata import load as metadata

    r = record().model_dump(mode="json")
    for key in ["mode", "verification", "fetched_at", "body", "module"]:
        r.pop(key)
    r.update(
        external_id="user-pin-metadata",
        title="Rotterdam user summary",
        url="https://pin.portofrotterdam.com/user-referenced-notice",
        summary="User summary: Rotterdam restriction active; verify original.",
        field_evidence={"operational_status": "Rotterdam restriction active"},
        rights_basis="user_authored_summary",
    )
    data = json.dumps([r]).encode()
    assert metadata(factory, data, "tester", "summary review")["inserted"] == 1
    assert metadata(factory, data, "tester", "repeat")["unchanged"] == 1
    with factory() as s:
        assert len(operations(s, "manual")) == 1
        assert not operations(s, "live")
    invalid = {**r, "rights_basis": "copied_webpage"}
    with pytest.raises(ValueError):
        metadata(factory, json.dumps([r, invalid]).encode(), "tester", "invalid")


def test_diesel_same_underlying_official_source_no_double_count(factory):
    # Synthetic row marked Manual, to exercise source-aware cross-space identity without fake Live.
    with factory.begin() as s:
        from scm.platform.diesel_import import Observation

        value = Observation.model_validate(diesel())
        from datetime import datetime, timezone

        register(
            s,
            [
                dict(
                    id="ec-weekly-fuel",
                    name="official observation test",
                    adapter="fixture",
                    url="https://energy.ec.europa.eu/data",
                )
            ],
        )
        body = "Synthetic manual test observation 2 EUR/litre"
        ingest(
            s,
            "ec-weekly-fuel",
            Record(
                external_id="official-test",
                module="market",
                title=body,
                body=body,
                url=value.source_url,
                fetched_at=utcnow(),
                observed_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
                mode="manual",
                verification="MANUAL",
                country="DE",
                value="2",
                currency="EUR",
                unit="EUR/litre",
                price_type="observed_price",
                evidence_quote=body,
            ),
        )
    assert (
        load(factory, json.dumps([diesel()]).encode(), "p.json", "tester", "same publisher")["unchanged"] == 1
    )
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(Item)) == 1


def test_subscription_permission_cannot_enable_html():
    from scm.collectors.http import AccessBlocked
    from scm.platform.service import specs

    spec = next(s for s in specs() if s["id"] == "hapag-ports-rss")
    permission_gate(spec, utcnow())
    with pytest.raises(AccessBlocked):
        permission_gate({**spec, "adapter": "html_list"}, utcnow())
    with pytest.raises(AccessBlocked):
        permission_gate({**spec, "url": "https://www.hapag-lloyd.com/en/news.html"}, utcnow())


def test_official_feed_parser_only_requests_feed():
    import httpx

    from scm.platform.adapters import fetch_records

    requested = []
    url = "https://www.hapag-lloyd.com/feeds/en/news/ports_inland.rss"
    rss = b"""<rss version="2.0"><channel><title>synthetic feed</title><item>
    <title>synthetic restriction</title><link>https://www.hapag-lloyd.com/synthetic</link>
    <description>synthetic only: no claim of a real event</description>
    <pubDate>Thu, 12 Nov 2026 10:00:00 +0000</pubDate></item></channel></rss>"""

    class Injected:
        verification_type = "TEST_CLIENT"

        def get(self, target):
            requested.append(target)
            return httpx.Response(200, content=rss)

    result, details = fetch_records(
        {"adapter": "subscription_rss", "module": "ports", "url": url, "reuse_policy": {"notice_url": url}},
        Injected(),
    )
    assert requested == [url]
    assert len(result) == 1 and result[0].mode == "demo"
    assert "no article HTTP" in details["content_scope"]
