"""Validate retained LIVE_HTTP evidence and the actual local UI; no synthetic seed.
Run from repository root after `scm collect --source ec --source ec-trade --source ec-industry`.
This command does not make fresh HTTP requests. It requires recent successful real collection logs.
"""

import argparse
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from streamlit.testing.v1 import AppTest

from scm.database.models import Analysis, Event, RawRevision, Source
from scm.database.session import session_factory
from scm.intelligence.service import ingest
from scm.reports.service import generate_report
from scm.schemas import RawArticle
from scm.settings import ROOT, TIMEZONE, utcnow

SOURCES = ["ec", "ec-trade", "ec-industry"]
PREFERRED = {
    "ec": "joint-press-release-19th-implementation",
    "ec-trade": "pet-spunbond",
    "ec-industry": "lift-buffer",
}


def validate(destination):
    factory = session_factory()
    evidence = []
    report_ids = []
    with factory.begin() as session:
        demo_before = session.scalar(select(func.count()).select_from(Event).where(Event.data_mode == "demo"))
        live_before = session.scalar(select(func.count()).select_from(Event).where(Event.data_mode == "live"))
        for source_id in SOURCES:
            source = session.get(Source, source_id)
            assert source is not None and source.last_status == "PASS", (
                f"{source_id}: no successful collection"
            )
            audit = json.loads(source.audit_json)
            assert audit["verification_type"] == "LIVE_HTTP", "Mock/Fixture is not live acceptance"
            assert audit["reuse_policy"]["status"] == "reviewed_allowed"
            assert source.last_success_at and utcnow() - datetime.fromisoformat(
                source.last_success_at
            ) < timedelta(hours=24)
            events = session.scalars(
                select(Event).where(Event.source_id == source_id, Event.data_mode == "live")
            ).all()
            assert events
            event = next((e for e in events if PREFERRED[source_id] in e.canonical_url), events[0])
            raw = session.scalar(
                select(RawRevision).where(
                    RawRevision.event_id == event.id, RawRevision.content_hash == event.content_hash
                )
            )
            analysis = session.scalar(
                select(Analysis).where(Analysis.event_id == event.id).order_by(Analysis.id.desc())
            )
            assert raw and raw.published_at and len(raw.body) >= 100 and analysis
            payload = json.loads(analysis.payload_json)
            assert payload["facts"] and all(
                fact["quote"] in raw.title + "\n" + raw.body for fact in payload["facts"]
            )
            status, same = ingest(
                session,
                RawArticle(
                    title=raw.title,
                    body=raw.body,
                    url=raw.source_url,
                    source=source_id,
                    published_at=datetime.fromisoformat(raw.published_at),
                    fetched_at=datetime.fromisoformat(event.fetched_at),
                    data_mode="live",
                ),
            )
            assert status == "unchanged" and same.id == event.id, (
                "repeat ingestion duplicated or changed evidence"
            )
            day = datetime.fromisoformat(event.published_at).astimezone(TIMEZONE).date()
            report = generate_report(session, "daily", "live", day)
            assert event.canonical_url in report.html and "CC BY 4.0" in report.html
            assert "example.invalid" not in report.html and "【演示】" not in report.html
            path = ROOT / "runtime/reports" / f"live-{day}.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report.html, encoding="utf-8")
            report_ids.append(report.id)
            evidence.append(
                {
                    "source": source_id,
                    "event_id": event.id,
                    "title": event.title,
                    "url": event.canonical_url,
                    "published_at": event.published_at,
                    "fetched_at": event.fetched_at,
                    "analyzed_at": analysis.analyzed_at,
                    "body_sha256": hashlib.sha256(raw.body.encode()).hexdigest(),
                    "risk_level": event.risk_level,
                    "risk_reasons": json.loads(event.risk_reasons_json),
                    "policy_status": event.policy_status,
                    "effective_at": event.effective_at,
                    "lifecycle": event.lifecycle,
                    "rule_version": event.rule_version,
                    "source_confidence": event.source_confidence,
                    "evidence_quote": payload["facts"][0]["quote"][:250],
                    "dedupe": "unchanged",
                    "daily_report_id": report.id,
                    "daily_report_day": str(day),
                    "source_collection": {
                        "status": source.last_status,
                        "dated_articles": audit["dated_articles"],
                        "stored_articles": audit["stored_articles"],
                        "last_success_at": source.last_success_at,
                    },
                }
            )
        assert (
            session.scalar(select(func.count()).select_from(Event).where(Event.data_mode == "live"))
            == live_before
        )
        assert (
            session.scalar(select(func.count()).select_from(Event).where(Event.data_mode == "demo"))
            == demo_before
        )
    app = AppTest.from_file(str(ROOT / "src/scm/ui/app.py"), default_timeout=45).run()
    assert not app.exception
    assert app.metric[0].value == str(live_before)
    assert not any("演示空间" in w.value for w in app.warning)
    app.sidebar.radio[1].set_value("Intelligence").run()
    assert not app.exception
    labels = [expander.label for expander in app.expander]
    assert all(any(row["title"] in label for label in labels) for row in evidence)
    assert any("CC BY 4.0" in caption.value for caption in app.caption)
    app.sidebar.radio[1].set_value("Reports").run()
    assert not app.exception
    for report_id in report_ids:
        selector = next(select for select in app.selectbox if select.label == "历史报告")
        selector.set_value(report_id).run()
        assert not app.exception
    result = {
        "status": "PASS",
        "verified_at": utcnow().astimezone(TIMEZONE).isoformat(),
        "verification": "Retained recent LIVE_HTTP evidence + local database + Streamlit AppTest; not a new HTTP run or human sign-off",
        "live_events": live_before,
        "demo_events": demo_before,
        "sources": evidence,
        "ui_pages": ["Overview", "Intelligence", "Reports"],
        "limitations": [
            "Three European Commission directorates, not three independent institutions.",
            "Historical articles reported on original publication dates, not re-dated to today.",
            "No user business/legal sign-off, real LLM, waiting-time or shipment-data validation.",
        ],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "live_events": live_before,
                "sources": len(evidence),
                "artifact": str(destination),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "runtime/live_acceptance.json")
    validate(parser.parse_args().output)
