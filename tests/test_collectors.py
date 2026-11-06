import json

import httpx
import pytest
from sqlalchemy import func, select

from scm.collectors.http import AccessBlocked, SafeFetcher
from scm.collectors.parsers import discover_links, parse_article, parse_date, parse_feed
from scm.collectors.service import run_collection
from scm.database.models import CollectionLog, Event, Source
from scm.intelligence.providers import OpenAICompatibleProvider
from scm.intelligence.service import ingest
from scm.schemas import RawArticle
from scm.settings import utcnow

HTML = """<html><head><meta property="article:published_time" content="2026-11-05T10:00:00Z"></head><body><article><h1>Hamburg port omission</h1><p>Hamburg port omission on a specific sailing has been announced. Customers should check the published carrier advisory and confirm whether their booking is affected.</p></article></body></html>"""


def make_fetcher(handler):
    return SafeFetcher(httpx.Client(transport=httpx.MockTransport(handler)), interval=0, retries=0)


def test_html_rss_date_and_discovery():
    article = parse_article(HTML, "https://official.test/news/1")
    assert article["published_at"].tzinfo and "Customers should" in article["body"]
    feed = parse_feed(
        b'<rss version="2.0"><channel><title>Test</title><item><title>News</title><link>https://official.test/news/1</link><pubDate>Thu, 05 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>'
    )
    assert len(feed) == 1 and feed[0]["published_at"].year == 2026
    links = discover_links(
        '<main><a href="/news/1">a</a><a href="/news/1">b</a><a href="https://other.test/news/2">c</a></main>',
        "https://official.test/news",
        "/news/",
    )
    assert links == ["https://official.test/news/1"]
    assert parse_date("not a date") is None
    assert (
        parse_article(HTML.replace("2026-11-05T10:00:00Z", "unknown"), "https://official.test")[
            "published_at"
        ]
        is None
    )


@pytest.mark.parametrize(
    "response, expected",
    [
        (httpx.Response(200, text="User-agent: *\nDisallow: /"), "disallows"),
        (httpx.Response(403), "robots.txt HTTP 403"),
        (httpx.Response(200, text="<html>challenge</html>"), "HTML/challenge"),
    ],
)
def test_robots_restrictions_stop_before_article(response, expected):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return response

    with pytest.raises(AccessBlocked, match=expected):
        make_fetcher(handler).get("https://official.test/news")
    assert seen == ["https://official.test/robots.txt"]


def test_cross_host_redirect_blocked():
    fetcher = make_fetcher(
        lambda request: httpx.Response(302, headers={"location": "https://other.test/robots.txt"})
    )
    with pytest.raises(AccessBlocked, match="Cross-host"):
        fetcher.get("https://official.test/news")


def test_retry_transient_and_rate_limit():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if calls.count("/news") == 1:
            return httpx.Response(503)
        return httpx.Response(200, text=HTML)

    fetcher = SafeFetcher(httpx.Client(transport=httpx.MockTransport(handler)), interval=0, retries=1)
    assert fetcher.get("https://official.test/news").status_code == 200
    assert calls.count("/news") == 2


def test_single_source_failure_isolated_and_live_idempotency(factory):
    def handler(request):
        if request.url.host == "blocked.test":
            return httpx.Response(403)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.url.path == "/news":
            return httpx.Response(200, text='<main><a href="/news/1">Official news</a></main>')
        return httpx.Response(200, text=HTML)

    specs = [
        {
            "id": "bad",
            "name": "Bad",
            "url": "https://blocked.test/news",
            "method": "html",
            "article_pattern": "/news/",
        },
        {
            "id": "good",
            "name": "Good",
            "url": "https://official.test/news",
            "method": "html",
            "article_pattern": "/news/",
        },
    ]
    first = run_collection(factory, specs, make_fetcher(handler))
    assert first[0]["status"] == "BLOCKED" and first[1]["status"] == "PASS"
    second = run_collection(factory, specs, make_fetcher(handler))
    assert second[1]["writes"] == {"unchanged": 1}
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(Event)) == 1
        assert s.scalar(select(func.count()).select_from(CollectionLog)) == 4
        event = s.scalar(select(Event))
        assert event.data_mode == "live" and event.canonical_url == "https://official.test/news/1"
        assert s.get(Source, "bad").last_status == "BLOCKED"


def test_rss_collects_full_page_not_summary(factory):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/feed.xml":
            return httpx.Response(
                200,
                text='<rss version="2.0"><channel><item><title>Test</title><link>https://official.test/news/1</link><description>short summary</description></item></channel></rss>',
            )
        return httpx.Response(200, text=HTML)

    specs = [{"id": "rss-test", "name": "RSS test", "url": "https://official.test/feed.xml", "method": "rss"}]
    assert run_collection(factory, specs, make_fetcher(handler))[0]["status"] == "PASS"
    with factory() as s:
        assert s.scalar(select(Event)).title == "Hamburg port omission"


def test_empty_js_page_not_success(factory):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text='<html><div id="app"></div></html>')

    result = run_collection(
        factory,
        [
            {
                "id": "js-test",
                "name": "JS test",
                "url": "https://official.test/news",
                "method": "html",
                "article_pattern": "/news/",
            }
        ],
        make_fetcher(handler),
    )
    assert result[0]["status"] == "BLOCKED"
    assert result[0]["access_success"] and not result[0]["body_obtained"]


def llm_env(monkeypatch):
    monkeypatch.setenv("SCM_LLM_API_KEY", "unit-test-not-real")
    monkeypatch.setenv("SCM_LLM_MODEL", "test-model")
    monkeypatch.setenv("SCM_LLM_BASE_URL", "https://llm.test/v1")


def llm_payload(quote):
    return {
        "title_zh": "汉堡航线调整",
        "facts": [{"text_zh": "汉堡港挂靠调整", "quote": quote}],
        "potential_impacts": ["可能影响交付"],
        "watch_indicators": ["承运人更新"],
        "suggested_actions": ["核实航次"],
    }


def test_optional_llm_evidence_validation_and_fallback(factory, monkeypatch):
    llm_env(monkeypatch)
    output = llm_payload("Invented factual statement not in original")
    provider = OpenAICompatibleProvider(
        httpx.Client(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(
                    200, json={"choices": [{"message": {"content": json.dumps(output)}}]}
                )
            )
        )
    )
    article = RawArticle(
        title="Hamburg port omission",
        body="Hamburg port omission. Customers should confirm their booking.",
        url="https://official.test/news/1",
        source="test",
        fetched_at=utcnow(),
    )
    with pytest.raises(ValueError, match="quote not found"):
        provider.analyze(article, {})
    with factory.begin() as s:
        s.add(Source(id="test", name="test", url="https://official.test", method="html"))
        s.flush()
        _, event = ingest(s, article, provider)
        from scm.database.models import Analysis

        analysis = s.scalar(select(Analysis).where(Analysis.event_id == event.id))
        assert analysis.provider == "rules-only" and analysis.error
        assert "Invented factual statement" not in analysis.payload_json
        assert event.risk_level == "中"


def test_optional_llm_valid_mock(monkeypatch):
    llm_env(monkeypatch)
    quote = "Hamburg port omission."
    provider = OpenAICompatibleProvider(
        httpx.Client(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(
                    200, json={"choices": [{"message": {"content": json.dumps(llm_payload(quote))}}]}
                )
            )
        )
    )
    article = RawArticle(
        title=quote,
        body="Customers should confirm their booking.",
        url="https://official.test/news/1",
        source="test",
        fetched_at=utcnow(),
    )
    assert provider.analyze(article, {})["facts"][0]["quote"] == quote


def test_redirect_cannot_fetch_robots_disallowed_path():
    seen = []

    def handler(request):
        seen.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private")
        return httpx.Response(302, headers={"location": "/private"})

    with pytest.raises(AccessBlocked, match="redirected URL"):
        make_fetcher(handler).get("https://official.test/news")
    assert seen == ["/robots.txt", "/news"]


def test_deterministic_proxy_403_not_retried():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        raise httpx.ProxyError("403 Forbidden")

    fetcher = SafeFetcher(httpx.Client(transport=httpx.MockTransport(handler)), interval=0, retries=2)
    with pytest.raises(httpx.ProxyError):
        fetcher.get("https://official.test/news")
    assert len(calls) == 1
