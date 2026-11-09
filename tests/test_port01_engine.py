from datetime import UTC, datetime, timedelta

import pytest

from scm.ports.engine import Notice, assess_notice, grounded_ports

NOW = datetime(2026, 11, 9, 8, tzinfo=UTC)


def notice(**patch):
    data = dict(
        external_id="47/2026",
        title="Hamburg port closure",
        body="Hamburg port is closed. ISO Tank dangerous goods are restricted.",
        url="https://official.test/notices/47",
        published_at=NOW - timedelta(hours=1),
        fetched_at=NOW,
        valid_from=NOW - timedelta(hours=2),
        valid_until=NOW + timedelta(hours=8),
    )
    return Notice(**(data | patch))


def test_closure_dual_axes_and_explicit_current_evidence():
    result = assess_notice(notice(), ["hamburg"], NOW)
    assert result["severity"] == "high" and result["relevance"] == "high"
    assert result["state"] == "confirmed_disruption" and result["lifecycle"] == "active"
    ordinary = assess_notice(notice(body="Hamburg port is closed."), ["hamburg"], NOW)
    assert ordinary["severity"] == "high" and ordinary["relevance"] == "low"


@pytest.mark.parametrize(
    "patch,state,lifecycle",
    [
        ({"body": "Hamburg port closure lifted. Operations have resumed."}, "unknown", "resolved"),
        (
            {
                "body": "Hamburg port closure is planned tomorrow.",
                "valid_from": NOW + timedelta(days=1),
                "valid_until": NOW + timedelta(days=2),
            },
            "unknown",
            "planned",
        ),
        (
            {"published_at": NOW - timedelta(days=3), "valid_from": None, "valid_until": None},
            "stale",
            "active",
        ),
        ({"fetched_at": NOW - timedelta(days=2)}, "stale", "active"),
        ({"published_at": None}, "stale", "active"),
        (
            {"valid_until": NOW - timedelta(minutes=1), "valid_from": NOW - timedelta(days=2)},
            "stale",
            "active",
        ),
        ({"verification_type": "INJECTED_TEST_CLIENT"}, "unknown", "active"),
    ],
)
def test_resolved_stale_future_and_test_evidence(patch, state, lifecycle):
    r = assess_notice(notice(**patch), ["hamburg"], NOW)
    assert r["state"] == state and r["lifecycle"] == lifecycle


def test_only_explicit_normal_not_absence_of_alerts():
    r = assess_notice(notice(title="Hamburg status", body="Hamburg operations are normal."), ["hamburg"], NOW)
    assert r["state"] == "confirmed_normal"
    r = assess_notice(
        notice(title="Hamburg news", body="Hamburg hosted a marketing event."), ["hamburg"], NOW
    )
    assert r["state"] == "unknown" and r["severity"] == "unknown"
    r = assess_notice(
        notice(title="Hamburg no port closure", body="Hamburg is not closed. No port closure is reported."),
        ["hamburg"],
        NOW,
    )
    assert r["state"] == "unknown" and r["severity"] == "unknown"


def test_port_omission_not_container_or_eta_claim():
    r = assess_notice(
        notice(title="Hamburg port omission", body="Hamburg port omission on a planned Europe sailing."),
        ["hamburg"],
        NOW,
    )
    assert r["kind"] == "port_omission" and r["severity"] == "medium" and r["state"] == "unknown"
    assert "ETA" in r["uncertainty"]


def test_grounded_location_and_shared_tees_scope():
    assert grounded_ports("London gateway terminal closure", ["dover"]) == []
    assert grounded_ports("Tangier city", ["tangier"]) == []
    assert grounded_ports("Tanger Med operations", ["tangier"]) == ["tangier"]
    assert grounded_ports("Bremerhaven not Hamburgshire", ["hamburg", "bremerhaven"]) == ["bremerhaven"]
    assert grounded_ports("River Tees navigation restriction", ["teesport", "middlesbrough"]) == [
        "teesport",
        "middlesbrough",
    ]
    assert grounded_ports("Teesport restrictions", ["teesport", "middlesbrough"]) == ["teesport"]


def test_demo_identifier_rejected_live_and_interval_timezone():
    with pytest.raises(ValueError):
        notice(external_id="DEMO-47")
    with pytest.raises(ValueError):
        notice(fetched_at=datetime(2026, 11, 9))
    with pytest.raises(ValueError):
        notice(valid_until=NOW - timedelta(days=3))
