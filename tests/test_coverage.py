"""Mock log records test accounting, not genuine LIVE validation."""

import json
from datetime import timedelta

import httpx

from scm.collectors.coverage import collection_coverage
from scm.collectors.http import SafeFetcher
from scm.collectors.service import run_collection
from scm.database.models import CollectionLog, Source
from scm.reports.service import generate_report, period_bounds
from scm.settings import TIMEZONE, utcnow


def setup_source(session):
    session.add(
        Source(
            id="coverage-test",
            name="Synthetic coverage test",
            url="https://official.test",
            method="html",
            enabled=True,
        )
    )
    session.flush()


def log_record(session, *, stamp=None, status="PASS", kind="LIVE_HTTP", dated=1):
    stamp = stamp or utcnow()
    session.add(
        CollectionLog(
            source_id="coverage-test",
            started_at=stamp.isoformat(),
            finished_at=stamp.isoformat(),
            status=status,
            collected=1,
            inserted=1,
            updated=0,
            error="Synthetic network refusal" if status == "BLOCKED" else None,
            details_json=json.dumps(
                {
                    "verification_type": kind,
                    "stored_articles": 1,
                    "parsed_articles": 1,
                    "dated_articles": dated,
                    "duration_ms": 100,
                }
            ),
        )
    )
    session.flush()


def test_failed_or_missing_sources_never_report_no_news(factory):
    with factory.begin() as s:
        setup_source(s)
        for kind in ["daily", "weekly"]:
            report = generate_report(s, kind, "live")
            assert "采集覆盖不足" in report.html
            assert "不能判断本期没有重要新增事件" in report.html
            assert "<p>本期没有重要新增事件" not in report.html
        log_record(s, status="BLOCKED")
        assert not collection_coverage(s, *period_bounds("daily"))["adequate"]
        assert "Synthetic network refusal" in generate_report(s, "daily", "live").html


def test_injected_mock_unknown_dates_and_stale_logs_cannot_prove_live_coverage(factory):
    with factory.begin() as s:
        setup_source(s)
        log_record(s, stamp=utcnow() - timedelta(days=2))
        assert not collection_coverage(s, *period_bounds("daily"))["adequate"]
        log_record(s, kind="INJECTED_TEST_CLIENT")
        assert not collection_coverage(s, *period_bounds("daily"))["adequate"]
        log_record(s, dated=0)
        assert not collection_coverage(s, *period_bounds("daily"))["adequate"]
        log_record(s)
        assert collection_coverage(s, *period_bounds("daily"))["adequate"]
        assert "本期已采集样本中未识别重要新增事件" in generate_report(s, "daily", "live").html
        log_record(s, status="BLOCKED")
        assert not collection_coverage(s, *period_bounds("daily"))["adequate"]


def test_weekly_requires_each_day_and_reports_missing_days(factory):
    with factory.begin() as s:
        setup_source(s)
        log_record(s)
        start, end = period_bounds("weekly")
        result = collection_coverage(s, start, end)
        if utcnow().astimezone(TIMEZONE).weekday() > 0:
            assert not result["adequate"]
            assert result["sources"][0]["failures"]


def test_collection_telemetry_marks_injected_data_and_preserves_last_success(factory):
    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/news":
            return httpx.Response(200, text='<main><a href="/news/1">Article</a></main>')
        return httpx.Response(
            200,
            text='<article><h1>Rotterdam operations update</h1><time datetime="2026-11-06T00:00:00Z"></time><p>Rotterdam operations suspended following an operational incident. Customers should verify the announcement with official authorities before changing shipment plans.</p></article>',
        )

    fetcher = SafeFetcher(httpx.Client(transport=httpx.MockTransport(handler)), interval=0, retries=0)
    specs = [
        {
            "id": "telemetry-test",
            "name": "Synthetic telemetry",
            "url": "https://official.test/news",
            "method": "html",
            "article_pattern": "/news/",
        }
    ]
    result = run_collection(factory, specs, fetcher)[0]
    assert result["status"] == "PASS" and result["verification_type"] == "INJECTED_TEST_CLIENT"
    assert result["duration_ms"] >= 0 and result["stored_articles"] == 1
    assert result["article_samples"][0]["published_at"]
    assert result["median_publication_age_hours"] is not None
    with factory() as s:
        assert s.get(Source, "telemetry-test").last_success_at is None
        assert not collection_coverage(s, *period_bounds("daily"))["adequate"]
