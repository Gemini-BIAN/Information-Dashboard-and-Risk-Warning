"""Repeat actual HTTP collection against runtime/phase2a/live.db and save evidence.
Requires a prior real run; invokes no fixtures, LLM or UI. Use timeout 160s.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from sqlalchemy import func, select

from scm.collectors.http import SafeFetcher
from scm.content.contracts import IntelligenceRecord
from scm.content.digest import generate_digest
from scm.content.service import collect_content
from scm.database.models import Analysis, Event, RawRevision
from scm.database.session import session_factory
from scm.settings import TIMEZONE, utcnow


def main():
    root = Path.cwd()
    folder = root / "runtime/phase2a"
    factory = session_factory("sqlite:///runtime/phase2a/live.db")
    with factory() as s:
        before = {
            t.__tablename__: s.scalar(select(func.count()).select_from(t))
            for t in [Event, RawRevision, Analysis]
        }
        first_ids = {e.id: (e.content_hash, e.published_at) for e in s.scalars(select(Event))}
    if not before["events"]:
        raise RuntimeError("Run the real permission-gated collector first; empty DB is not live acceptance")
    specs = json.loads((root / "config/phase2a_sources.json").read_text())
    f = SafeFetcher(retries=0)
    traces = []
    captures = {}

    def trace(response):
        traces.append({"url": str(response.request.url), "http_status": response.status_code})

    f.client.event_hooks = {"response": [trace]}
    original = f.get

    def capture(url):
        response = original(url)
        if "/en/press/news/" in url or "/news/" in url:
            soup = BeautifulSoup(response.text, "html.parser")
            if soup.h1:
                captures[url] = {
                    "title": soup.h1.get_text(" ", strip=True),
                    "visible_header": soup.h1.find_next("p").get_text(" ", strip=True)[:180],
                    "response_html_sha256": hashlib.sha256(response.content).hexdigest(),
                    "canonical": soup.find("link", rel="canonical").get("href")
                    if soup.find("link", rel="canonical")
                    else url,
                }
        return response

    f.get = capture
    try:
        results = collect_content(factory, specs, f)
    finally:
        f.close()
    with factory() as s:
        after = {
            t.__tablename__: s.scalar(select(func.count()).select_from(t))
            for t in [Event, RawRevision, Analysis]
        }
        assert before == after
        records = []
        for e in s.scalars(select(Event)):
            assert first_ids[e.id] == (e.content_hash, e.published_at)
            a = s.scalar(select(Analysis).where(Analysis.event_id == e.id).order_by(Analysis.id.desc()))
            v = IntelligenceRecord.model_validate(json.loads(a.payload_json)["content_v1"])
            raw = s.scalar(
                select(RawRevision).where(
                    RawRevision.event_id == e.id, RawRevision.content_hash == e.content_hash
                )
            )
            assert v.source_published_at.isoformat() == raw.published_at == e.published_at
            assert v.evidence_snippets[0].quote in raw.body
            assert v.data_mode == "live" and a.provider == "rules-only"
            assert v.operational_state != "confirmed_current_disruption"
            records.append(
                {
                    "event_id": e.id,
                    "url": e.canonical_url,
                    "source_id": e.source_id,
                    "organization_id": v.organization_id,
                    "title": e.title,
                    "published_at": e.published_at,
                    "raw_content_fingerprint": raw.content_hash,
                    "date_integrity": True,
                    "verbatim_evidence": True,
                    "raw_revision_id": raw.id,
                    "body_characters": len(raw.body),
                    "relevance": v.business_relevance.model_dump(mode="json"),
                    "risk_level": e.risk_level,
                    "risk_reasons": json.loads(e.risk_reasons_json),
                    "lifecycle": e.lifecycle,
                    "operational_state": v.operational_state,
                    "quality_flags": v.quality_flags,
                }
            )
        document, summary = generate_digest(s, utcnow().astimezone(TIMEZONE).date())
        (folder / "daily.html").write_text(document)
        from collections import Counter

        evidence = {
            "verified_at": utcnow().isoformat(),
            "verification_type": "LIVE_HTTP",
            "attempt": "repeat after first real ingestion",
            "before_counts": before,
            "after_counts": after,
            "source_results": results,
            "request_trace": traces,
            "independent_header_capture": captures,
            "records": records,
            "new_live_records_first_run": before["events"],
            "repeat_new_records": sum(r.get("writes", {}).get("inserted", 0) for r in results),
            "organizations_total": len({r["organization_id"] for r in records}),
            "new_organizations_beyond_ec_baseline": len(
                {r["organization_id"] for r in records} - {"european-commission"}
            ),
            "relevance_counts": dict(Counter(r["relevance"]["decision"] for r in records)),
            "fresh_within_7_days": sum(
                0 <= (utcnow() - datetime.fromisoformat(r["published_at"])).total_seconds() <= 7 * 86400
                for r in records
            ),
            "digest": summary,
            "html_sha256": hashlib.sha256(document.encode()).hexdigest(),
        }
        Path("docs/PHASE2_LIVE_EVIDENCE.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
        )
        print(
            json.dumps(
                {
                    k: v
                    for k, v in evidence.items()
                    if k not in ["records", "source_results", "request_trace", "independent_header_capture"]
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
