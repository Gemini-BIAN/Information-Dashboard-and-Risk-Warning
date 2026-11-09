import json
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import func, select

from scm.collectors.http import AccessBlocked, SafeFetcher
from scm.database.models import Event, PortAlert, PortSignal
from scm.ports.collector import collect
from scm.ports.demo import seed
from scm.ports.engine import Notice
from scm.ports.registry import source_specs
from scm.ports.report import daily
from scm.ports.service import analyze, permission_gate, read_alert, snapshots, store_notice
from scm.settings import utcnow


def source(now):
    return dict(
        id="test",
        name="Synthetic permitted source",
        url="https://official.test/feed",
        ports=["teesport", "middlesbrough", "hamburg"],
        permission="allowed_full_text",
        automatic_access_allowed=True,
        audit_ref="synthetic fixture only",
        terms_url="https://official.test/legal",
        permission_verified_at=now.isoformat(),
        method="rss_text",
    )


def synthetic(now, **patch):
    return Notice(
        **(
            dict(
                external_id="47/2026",
                title="River Tees closure",
                body="River Tees port is closed. ISO Tank dangerous goods restrictions are in force.",
                url="https://official.test/47",
                published_at=now - timedelta(minutes=5),
                fetched_at=now,
                valid_from=now - timedelta(hours=1),
                valid_until=now + timedelta(hours=12),
            )
            | patch
        )
    )


def test_stable_identity_dedup_escalation_resolution_and_mode_read(factory):
    now = utcnow()
    src = source(now)
    with factory.begin() as session:
        first = synthetic(
            now,
            title="River Tees port omission",
            body="River Tees port omission is planned for an Europe service.",
        )
        store_notice(session, src, first, now)
        store_notice(session, src, first, now)
        assert session.scalar(select(func.count(PortAlert.id))) == 1
        store_notice(session, src, synthetic(now), now)
        assert session.scalar(select(func.count(PortAlert.id))) == 2
        resolved = synthetic(
            now,
            url="https://official.test/47-revised",
            body="River Tees closure lifted. Operations have resumed.",
        )
        store_notice(session, src, resolved, now)
        assert session.scalar(select(func.count(PortSignal.id))) == 1
        alerts = list(session.scalars(select(PortAlert).order_by(PortAlert.id)))
        assert [a.kind for a in alerts] == ["new", "escalation", "resolution"]
        assert json.loads(alerts[0].summary_json)["assessment"]["ports"] == ["teesport", "middlesbrough"]
        with pytest.raises(ValueError):
            read_alert(session, alerts[0].id, "demo")
        read_alert(session, alerts[0].id, "live")
        assert alerts[0].read_at
    with factory() as session:
        assert all(snap["state"] == "unknown" for snap in snapshots(session, "live").values())
        html = daily(session, "live").html
        assert html.count("<article>") == 1 and "resolution" in html and "共享事件只计一次" in html
        assert "DEMO" not in html


def test_all_actual_sources_gate_zero_network_and_rotterdam(factory):
    calls = []
    f = SafeFetcher(
        httpx.Client(transport=httpx.MockTransport(lambda r: calls.append(r) or httpx.Response(500))),
        retries=0,
    )
    results = collect(factory, fetcher=f)
    assert len(results) == len(source_specs()) and not calls
    assert all(r["requests"] == 0 and r["status"] == "BLOCKED" for r in results)
    assert any(r["source"] == "rotterdam-restricted" for r in results)
    with factory() as s:
        assert s.scalar(select(func.count(Event.id))) == 0
    f.close()


def test_approved_rss_adapter_isolation_and_repeat_is_only_mock(factory):
    now = utcnow()
    good = source(now)
    bad = source(now) | {"id": "denied", "permission": "unknown"}
    feed = f"""<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><title>Synthetic</title><item><guid>47/2026</guid><link>https://official.test/47</link><title>River Tees port omission</title><pubDate>{now.strftime("%a, %d %b %Y %H:%M:%S GMT")}</pubDate><content:encoded><![CDATA[River Tees port omission is planned. This is a synthetic test, not real news.]]></content:encoded></item></channel></rss>"""

    def handler(request):
        return httpx.Response(
            200, text="User-agent: *\nAllow: /" if request.url.path == "/robots.txt" else feed
        )

    f = SafeFetcher(httpx.Client(transport=httpx.MockTransport(handler)), interval=0, retries=0)
    rows = collect(factory, [bad, good], f)
    assert rows[0]["requests"] == 0 and rows[1]["inserted"] == 1
    assert collect(factory, [good], f)[0]["unchanged"] == 1
    with factory() as s:
        assert s.scalar(select(func.count(PortAlert.id))) == 1
        assert s.scalar(select(func.count(PortSignal.id))) == 1
    f.close()


def test_ai_failure_or_ungrounded_quote_falls_back_without_risk_override():
    now = utcnow()
    n = synthetic(now)

    class Broken:
        name = "fake"

        def analyze(self, *args):
            raise RuntimeError("secret must not leak")

    result = analyze(n, {}, Broken())
    assert result["mode"] == "rules-fallback" and "secret" not in result["note"]

    class Hallucination:
        name = "fake"

        def analyze(self, *args):
            return {
                "title_zh": "虚构",
                "facts": [{"text_zh": "虚构", "quote": "not in source"}],
                "potential_impacts": [],
                "watch_indicators": [],
                "suggested_actions": [],
            }

    assert analyze(n, {}, Hallucination())["mode"] == "rules-fallback"
    assert analyze(n, {})["facts"][0]["quote"] in n.body


def test_demo_is_explicit_idempotent_and_never_live(factory):
    seed(factory)
    seed(factory)
    with factory() as s:
        assert s.scalar(select(func.count(PortSignal.id))) == 2
        assert s.scalar(select(func.count(PortAlert.id))) == 2
        assert not any(x["events"] for x in snapshots(s, "live").values())
        assert len(snapshots(s, "demo")["teesport"]["events"]) == 1
        assert "DEMO" in daily(s, "demo").html
        assert "DEMO" not in daily(s, "live").html


def test_permission_expiry_blocks_even_previously_allowed():
    now = utcnow()
    spec = source(now) | {"permission_verified_at": (now - timedelta(days=31)).isoformat()}
    with pytest.raises(AccessBlocked):
        permission_gate(spec, now)


def test_cancelled_numbered_notice_inherits_prior_scope_without_new_alert_duplicate(factory):
    now = utcnow()
    src = source(now)
    with factory.begin() as session:
        store_notice(session, src, synthetic(now), now)
        cancellation = synthetic(now, title="Notice 47 CANCELLED", body="Numbered notice 47/2026 CANCELLED.")
        store_notice(session, src, cancellation, now)
        store_notice(session, src, cancellation, now)
        signal = session.scalar(select(PortSignal))
        data = json.loads(signal.payload_json)
        assert data["assessment"]["ports"] == ["teesport", "middlesbrough"]
        assert data["assessment"]["lifecycle"] == "resolved"
        assert session.scalar(select(func.count(PortAlert.id))) == 2


def test_additive_migration_preserves_existing_demo_evidence(factory):
    from alembic import command
    from alembic.config import Config

    from scm.collectors.service import load_demo
    from scm.settings import ROOT

    load_demo(factory)
    engine = factory.kw["bind"]
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.downgrade(cfg, "002")
        before = connection.exec_driver_sql(
            "select id,canonical_url,content_hash from events order by id"
        ).fetchall()
        command.upgrade(cfg, "head")
        after = connection.exec_driver_sql(
            "select id,canonical_url,content_hash from events order by id"
        ).fetchall()
        assert before == after and len(after) == 5
