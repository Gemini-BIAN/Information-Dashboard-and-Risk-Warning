"""Coverage measures collection evidence, never absence of real-world events."""

import json
from datetime import datetime, timedelta

from sqlalchemy import select

from scm.database.models import CollectionLog, Source
from scm.settings import TIMEZONE, utcnow


def collection_coverage(session, start, end, now=None):
    now = now or utcnow()
    end = min(end, now)
    sources = list(
        session.scalars(select(Source).where(Source.enabled.is_(True), Source.method != "fixture"))
    )
    days = set()
    cursor = start.astimezone(TIMEZONE).date()
    while end > start and cursor <= (end - timedelta(microseconds=1)).astimezone(TIMEZONE).date():
        days.add(cursor.isoformat())
        cursor += timedelta(days=1)
    details = []
    for source in sources:
        logs = session.scalars(
            select(CollectionLog)
            .where(CollectionLog.source_id == source.id)
            .order_by(CollectionLog.finished_at, CollectionLog.id)
        ).all()
        latest_per_day = {}
        for log in logs:
            stamp = datetime.fromisoformat(log.finished_at)
            if start <= stamp < end:
                latest_per_day[stamp.astimezone(TIMEZONE).date().isoformat()] = log
        covered = []
        failures = []
        durations = []
        for day in sorted(days):
            log = latest_per_day.get(day)
            audit = json.loads(log.details_json) if log else {}
            valid = bool(
                log
                and log.status == "PASS"
                and audit.get("verification_type") == "LIVE_HTTP"
                and audit.get("stored_articles", 0) > 0
                and audit.get("dated_articles") == audit.get("parsed_articles")
                and audit.get("dated_articles", 0) > 0
            )
            if valid:
                covered.append(day)
            else:
                failures.append({"day": day, "reason": log.error or log.status if log else "NOT TESTED"})
            if log and audit.get("duration_ms") is not None:
                durations.append(audit["duration_ms"])
        details.append(
            {
                "source": source.id,
                "name": source.name,
                "covered_days": covered,
                "required_days": sorted(days),
                "failures": failures,
                "last_success_at": source.last_success_at,
                "duration_ms": durations,
                "complete": bool(days) and len(covered) == len(days),
            }
        )
    adequate = bool(details) and all(d["complete"] for d in details)
    return {
        "adequate": adequate,
        "covered_sources": sum(d["complete"] for d in details),
        "configured_sources": len(details),
        "sources": details,
        "note": "仅衡量配置来源的有限样本采集，不保证全站/全球完整覆盖；Mock/Fixture、未知日期、失败或缺少当期日志均不能证明Live覆盖。",
    }
