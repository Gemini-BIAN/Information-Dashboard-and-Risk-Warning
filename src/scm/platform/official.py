"""Bounded official documents and feed-only subscription; never follows feed article links."""

import re
from datetime import datetime
from urllib.parse import urlsplit

import feedparser
from bs4 import BeautifulSoup

from scm.platform.adapters import _record


def fetch(spec, fetcher):
    response = fetcher.get(spec["url"])
    if spec["adapter"] == "subscription_rss":
        feed = feedparser.parse(response.content)
        if feed.bozo or not feed.version:
            raise ValueError("Invalid official subscription RSS")
        records = []
        for entry in feed.entries[:10]:
            if urlsplit(entry.link).hostname != urlsplit(spec["url"]).hostname:
                raise ValueError("Unapproved evidence host")
            body = BeautifulSoup(entry.get("description", ""), "html.parser").get_text(" ", strip=True)
            if not body or not entry.get("published_parsed"):
                continue
            from email.utils import parsedate_to_datetime

            rec = _record(
                spec,
                entry.title,
                body,
                entry.link,
                parsedate_to_datetime(entry.published),
                fetcher.verification_type,
                entry.get("id", entry.link),
            )
            # Only reviewed, explicit source facts are typed; other feed items remain background.
            claim = next(
                (
                    q
                    for q in [
                        "This restriction is effective immediately and will remain in place until further notice.",
                        "rail services to and from London Gateway are currently suspended due to a train derailment",
                    ]
                    if q in body
                ),
                None,
            )
            if claim:
                rec = type(rec).model_validate(
                    {
                        **rec.model_dump(),
                        "operational_event_id": ("DEMO-" if rec.mode == "demo" else "") + entry.link,
                        "operational_status": "active",
                        "country": "GB" if "rail services" in claim else "ES",
                        "location": "London Gateway" if "rail services" in claim else "APMT Valencia",
                        "event_scope": "carrier_service",
                        "status_at": rec.published_at,
                        "transport": "rail" if "rail services" in claim else "container_gate_in",
                        "field_evidence": {"operational_status": claim},
                    }
                )
            records.append(rec)
        return records, {
            "content_scope": "official RSS description only; no article HTTP requests",
            "subscription_notice": spec["reuse_policy"]["notice_url"],
        }
    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.select_one(".gem-c-govspeak")
    title = soup.select_one("h1")
    published = soup.select_one('meta[name="govuk:first-published-at"]')
    if published is None:
        # Visible first publication, never govuk:updated-at (site maintenance timestamp).
        published = soup.select_one(".gem-c-published-dates time")
    if not container or not title or not published:
        raise ValueError("GOV.UK required body/title/first publication missing")
    stamp = published.get("content") or published.get("datetime")
    body = container.get_text(" ", strip=True)
    body = re.sub(r"\s+", " ", body)
    rec = _record(
        spec,
        title.get_text(" ", strip=True),
        body,
        spec["url"],
        datetime.fromisoformat(stamp.replace("Z", "+00:00")),
        fetcher.verification_type,
    )
    # Curated, literal claim mapping. A changed sentence fails closed; no guessed status/numbers.
    fields = spec["project_fields"]
    quotes = spec["field_evidence"]
    if any(q not in body for q in quotes.values()):
        raise ValueError("Official project text changed; field extraction requires review")
    return [
        type(rec).model_validate(
            {
                **rec.model_dump(),
                **fields,
                "field_evidence": quotes,
                "evidence_quote": quotes["project_status"],
            }
        )
    ], {
        "attribution": "Contains public sector information licensed under OGL v3.0; extracted/structured",
        "publication_precision": "original visible publication; date-only is midnight offset convention",
        "identity_basis": spec["identity_basis"],
    }
