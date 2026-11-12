"""One bounded local increment; external task scheduling must be user configured."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from scm.platform.adapters import collect
from scm.platform.decision import refresh
from scm.platform.decision_io import decision_report, source_health
from scm.platform.models import PlatformSource
from scm.platform.service import register, specs
from scm.settings import utcnow


def update(factory, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with factory.begin() as session:
        register(session)
        checks = {s.id: s.last_checked_at for s in session.scalars(select(PlatformSource))}
    due = [
        s
        for s in specs()
        if s.get("enabled")
        and (
            not checks.get(s["id"])
            or datetime.fromisoformat(checks[s["id"]]) + timedelta(minutes=s["frequency_minutes"]) <= utcnow()
        )
    ]
    results = collect(factory, due)
    with factory.begin() as session:
        decisions = refresh(session, "live")
        for kind in ["daily", "weekly"]:
            report = decision_report(session, "live", kind)
            (output_dir / f"live-decision-{kind}.html").write_text(report.html, encoding="utf-8")
        health = source_health(session)
    summary = {
        "at": utcnow().isoformat(),
        "collection": results,
        "decisions": decisions,
        "sources": health,
        "note": "No DEMO seeding, no external messages, no persistent background service",
    }
    (output_dir / "update.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary
