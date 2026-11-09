"""Permission-gated RSS text adapter. No enabled live feeds until permissions clear."""

import json

import feedparser
from bs4 import BeautifulSoup

from scm.collectors.http import AccessBlocked, SafeFetcher
from scm.collectors.parsers import parse_date
from scm.database.models import CollectionLog, Source
from scm.ports.engine import Notice
from scm.ports.registry import source_specs
from scm.ports.service import permission_gate, store_notice
from scm.settings import utcnow


def collect(factory, specs=None, fetcher=None):
    owned = fetcher is None
    fetcher = fetcher or SafeFetcher(retries=0)
    results = []
    try:
        for source in specs if specs is not None else source_specs():
            started = utcnow()
            count = fetcher.request_count
            row = {
                "source": source["id"],
                "status": "BLOCKED",
                "stage": "permission",
                "inserted": 0,
                "updated": 0,
                "unchanged": 0,
            }
            try:
                permission_gate(source, started)
                if source.get("method") != "rss_text":
                    raise AccessBlocked("No approved adapter; no requests")
                row["stage"] = "robots_or_feed"
                response = fetcher.get(source["url"])
                feed = feedparser.parse(response.content)
                if feed.bozo and not feed.entries:
                    raise ValueError("Invalid RSS; not a successful collection")
                row["stage"] = "entry_parse_or_store"
                errors = []
                with factory.begin() as session:
                    for entry in feed.entries[:3]:
                        try:
                            content = entry.get("content", [{}])[0].get("value")
                            if not content:
                                raise ValueError("No permitted feed text; never synthesize article body")
                            body = BeautifulSoup(content, "html.parser").get_text(" ", strip=True)
                            notice = Notice(
                                external_id=entry.get("id") or entry.link,
                                title=entry.title,
                                body=body,
                                url=entry.link,
                                published_at=parse_date(entry.get("published")),
                                fetched_at=utcnow(),
                                valid_from=parse_date(entry.get("valid_from")),
                                valid_until=parse_date(entry.get("valid_until")),
                                verification_type=fetcher.verification_type,
                            )
                            with session.begin_nested():
                                outcome, _ = store_notice(session, source, notice)
                                row[outcome] += 1
                        except Exception as exc:
                            errors.append(type(exc).__name__)
                    row["errors"] = errors
                    row["status"] = (
                        "PASS"
                        if sum(row[x] for x in ["inserted", "updated", "unchanged"]) and not errors
                        else "PARTIAL"
                        if sum(row[x] for x in ["inserted", "updated", "unchanged"])
                        else "BLOCKED"
                    )
            except Exception as exc:
                row["error"] = (
                    type(exc).__name__ + ": " + str(exc)[:220]
                    if isinstance(exc, AccessBlocked)
                    else type(exc).__name__
                )
            row["requests"] = fetcher.request_count - count
            row["verification_type"] = fetcher.verification_type
            row["checked_at"] = utcnow().isoformat()
            with factory.begin() as session:
                id = "port01-" + source["id"]
                src = session.get(Source, id)
                if src is None:
                    src = Source(
                        id=id,
                        name=source["name"],
                        url=source["url"],
                        method="port-operational",
                        enabled=False,
                    )
                    session.add(src)
                    session.flush()
                src.last_status = row["status"]
                src.audit_json = json.dumps(row, ensure_ascii=False)
                if row["requests"]:
                    src.last_checked_at = row["checked_at"]
                session.add(
                    CollectionLog(
                        source_id=id,
                        started_at=started.isoformat(),
                        finished_at=row["checked_at"],
                        status=row["status"],
                        collected=sum(row[x] for x in ["inserted", "updated", "unchanged"]),
                        inserted=row["inserted"],
                        updated=row["updated"],
                        error=row.get("error"),
                        details_json=json.dumps(row),
                    )
                )
            results.append(row)
    finally:
        if owned:
            fetcher.close()
    return results
