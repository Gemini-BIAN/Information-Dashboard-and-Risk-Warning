"""Offline tests based on attributed real EU excerpts; NOT LIVE requests."""

import hashlib
import json
from datetime import datetime

import pytest

from scm.collectors.parsers import parse_article
from scm.risk.rules import classify, grade
from scm.settings import ROOT

FIXTURES = ROOT / "fixtures/official"
MANIFEST = json.loads((FIXTURES / "provenance.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("record", MANIFEST, ids=lambda v: v["source_id"])
def test_official_excerpt_title_date_and_verbatim_evidence(record):
    html = (FIXTURES / record["file"]).read_text(encoding="utf-8")
    assert hashlib.sha256(html.encode()).hexdigest() == record["fixture_sha256"]
    article = parse_article(html, record["url"], "european_commission")
    assert article["title"] == record["title"]
    assert article["published_at"] == datetime.fromisoformat(record["published_at"])
    assert record["quote"] in article["body"]
    assert record["test_type"] == "OFFICIAL_EXCERPT_FIXTURE_NOT_LIVE"
    if record["source_id"] == "ec-trade":
        assert "polyethylene terephthalate" in article["body"]  # lead is outside article in actual page
        assert "39.8% to 48.1%" in article["body"]
        assert classify(article["title"], article["body"])["event_type"] == "关税贸易"
        assert grade(article["title"], article["body"], "关税贸易")[0] == "中"


def test_ec_adapter_does_not_treat_listing_shell_as_article():
    with pytest.raises(ValueError, match="content container"):
        parse_article(
            "<main><h1>News</h1><p>" + ("Listing summary. " * 20) + "</p></main>",
            "https://policy.trade.ec.europa.eu/news_en",
            "european_commission",
        )
