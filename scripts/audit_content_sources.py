"""Phase-one metadata audit only: no article ingestion, database or production changes."""

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from scm.collectors.http import USER_AGENT, SafeFetcher
from scm.content.contracts import SourceRegistry

ROOT = Path(__file__).resolve().parents[1]


def main():
    registry = SourceRegistry.model_validate_json((ROOT / "config/content_sources.v1.json").read_text())
    results = []
    for source in registry.sources:
        start = time.monotonic()
        row = {
            "source_id": source.source_id,
            "url": str(source.url),
            "checked_at": datetime.now(UTC).isoformat(),
            "status": "NOT TESTED",
            "stage": "restriction_review",
            "trace": [],
            "body_extraction": "NOT TESTED: phase one metadata only",
            "fresh_article_count": None,
            "terms_status": "NOT TESTED",
            "publication_date": None,
        }

        def trace(response):
            row["trace"].append({"url": str(response.request.url), "http_status": response.status_code})

        client = httpx.Client(
            timeout=httpx.Timeout(10, connect=6),
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
            event_hooks={"response": [trace]},
        )
        fetcher = SafeFetcher(client=client, retries=0)
        try:
            if source.known_restriction:
                row["status"] = "BLOCKED"
                row["reason"] = source.known_restriction
                row["checked_at"] = None
                row["restriction_reviewed_at"] = datetime.now(UTC).isoformat()
            else:
                row["stage"] = "robots/listing"
                response = fetcher.get(str(source.url))
                soup = BeautifulSoup(response.text, "html.parser")
                row["page_title"] = soup.title.get_text(" ", strip=True)[:240] if soup.title else None
                row["metadata_dates"] = [
                    x.get("content") or x.get("datetime")
                    for x in soup.select('meta[property="article:published_time"], time[datetime]')
                ][:3]
                row["publication_date"] = row["metadata_dates"][0] if row["metadata_dates"] else None
                row["status"] = "PARTIAL"
                row["reason"] = (
                    "Listing accessible; article dates, freshness, body reuse and connector not accepted."
                )
                row["stage"] = "terms"
                if source.terms_url:
                    legal = fetcher.get(str(source.terms_url))
                    legal_soup = BeautifulSoup(legal.text, "html.parser")
                    row["terms_status"] = "HTTP accessible; manual license review required"
                    row["terms_title"] = (
                        legal_soup.title.get_text(" ", strip=True)[:240] if legal_soup.title else None
                    )
                row["stage"] = "completed_metadata_audit"
        except Exception as exc:
            row["error_type"] = type(exc).__name__
            row["error"] = str(exc)[:500]
            if row["status"] != "PARTIAL":
                row["status"] = "BLOCKED"
        finally:
            row["robots"] = fetcher.robots_audit
            row["elapsed_seconds"] = round(time.monotonic() - start, 2)
            fetcher.close()
        results.append(row)
        (ROOT / "docs/content_source_audit.v1.json").write_text(
            json.dumps(
                {"verification_type": "LIVE_HTTP", "attempts_per_source": 1, "results": results},
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        print(source.source_id, row["status"], row["stage"], flush=True)


if __name__ == "__main__":
    main()
