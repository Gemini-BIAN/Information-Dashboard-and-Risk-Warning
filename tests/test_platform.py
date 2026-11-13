import csv
import io
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import func, select

from scm.collectors.http import SafeFetcher
from scm.platform.adapters import collect, import_file
from scm.platform.contracts import Record
from scm.platform.models import Alert, Evidence, Item, PlatformSource, Report, Review
from scm.platform.service import assess, generate_report, ingest, register, review, rows, set_alert
from scm.settings import ROOT, utcnow

NOW = datetime(2026, 11, 11, 6, tzinfo=timezone.utc)


def record(module="capacity", **overrides):
    raw = dict(
        external_id="DEMO-1",
        module=module,
        title="DEMO project delayed",
        body="DEMO fictional battery project delayed construction. Capacity is not operating.",
        url="https://example.invalid/demo-1",
        published_at=NOW,
        fetched_at=NOW,
        mode="demo",
        verification="DEMO",
    )
    return Record.model_validate({**raw, **overrides})


def source(module="capacity", **overrides):
    result = dict(
        id="approved",
        name="DEMO approved source contract",
        module=module,
        url="https://official.test/list",
        adapter="html_list",
        method="html",
        article_pattern="/news/",
        parser="generic",
        limit=2,
        enabled=True,
        automatic_access_allowed=True,
        frequency_minutes=360,
        reuse_policy=dict(
            status="reviewed_allowed",
            permission="allowed_full_text",
            verified_at=utcnow().isoformat(),
            notice_url="https://official.test/terms",
            evidence_ref="SYNTHETIC TEST ONLY",
            license="synthetic",
        ),
    )
    return {**result, **overrides}


@pytest.mark.parametrize("module", ["ports", "capacity", "market"])
def test_module_vertical_flow_empty_duplicate_update_review_report_alert(factory, module):
    with factory.begin() as s:
        register(s, [source(module)])
        assert rows(s, "demo", module) == []
        generate_report(s, "demo", day=NOW)
        assert "本期没有" in s.scalar(select(Report)).html
        outcome, item = ingest(s, "approved", record(module), now=NOW)
        assert outcome == "inserted"
        assert (
            ingest(s, "approved", record(module, fetched_at=NOW + timedelta(hours=1)), now=NOW)[0]
            == "unchanged"
        )
        review(s, item.id, "demo", "confirmed", "checked the synthetic evidence", "tester")
        assert s.scalar(select(Review)).reason
        assert (
            ingest(
                s,
                "approved",
                record(
                    module,
                    body="DEMO fictional revised project delayed construction.",
                    fetched_at=NOW + timedelta(hours=2),
                ),
                now=NOW,
            )[0]
            == "updated"
        )
        assert item.review_status == "pending"
        assert len(list(s.scalars(select(Evidence)))) == 2
        assert s.scalar(select(Evidence).where(Evidence.version == 1)).raw_json.find("not operating") > 0
        a = s.scalar(select(Alert))
        set_alert(s, a.id, "demo", "read")
        with pytest.raises(ValueError):
            set_alert(s, a.id, "live", "handled")
        assert len(rows(s, "demo", module)) == 1 and rows(s, "live") == [] and rows(s, "manual") == []
        assert "DEMO" in generate_report(s, "demo", "daily", NOW).html
        assert "DEMO" in generate_report(s, "demo", "weekly", NOW).html
        assert s.scalar(select(func.count()).select_from(Item)) == 1


@pytest.mark.parametrize("module", ["ports", "capacity", "market"])
def test_module_collection_isolated_failure_and_mock_never_live(factory, module):
    spec = source(module)
    html = (
        '<h1>DEMO project delayed</h1><time datetime="2026-11-11T00:00:00Z"></time><article><p>'
        + ("DEMO battery factory project delayed construction; requires verification. " * 4)
        + "</p></article>"
    )

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.url.path == "/list":
            return httpx.Response(
                200, text='<main><a href="/news/good">good</a><a href="/news/broken">broken</a></main>'
            )
        if request.url.path == "/news/good":
            return httpx.Response(200, text=html)
        return httpx.Response(500)

    fetcher = SafeFetcher(client=httpx.Client(transport=httpx.MockTransport(handler)), interval=0, retries=0)
    blocked = {**spec, "id": "blocked", "enabled": False}
    first = collect(factory, [blocked, spec], fetcher)
    second = collect(factory, [spec], fetcher)
    assert first[0]["requests"] == 0 and first[0]["status"] == "unavailable"
    assert first[1]["writes"] == {"inserted": 1} and first[1]["errors"]
    assert second[0]["writes"] == {"unchanged": 1}
    with factory() as s:
        assert len(rows(s, "demo", module)) == 1 and not rows(s, "live")
        assert s.get(PlatformSource, "approved").last_success_at is None
        assert s.scalar(select(func.count()).select_from(Alert)) == 1
        assert rows(s, "demo", module)[0]["analysis"]["risk_level"] == "medium"
        assert "DEMO project delayed" in generate_report(s, "demo", day=NOW).html


@pytest.mark.parametrize("module", ["ports", "capacity", "market"])
def test_module_empty_bad_input_and_rollback(factory, module):
    with factory.begin() as s:
        register(s, [source(module)])
    with pytest.raises(ValueError):
        record(module, body="")
    with pytest.raises(ValueError):
        with factory.begin() as s:
            ingest(s, "approved", record(module), now=NOW)
            raise ValueError("transaction failure")
    with factory() as s:
        assert not rows(s, "demo", module)


@pytest.mark.parametrize(
    "overrides",
    [
        {"mode": "live"},
        {"mode": "manual"},
        {"verification": "LIVE_HTTP"},
        {"title": "not marked"},
        {"fetched_at": "2026-11-11T00:00:00"},
        {"published_at": "bad"},
        {"country": "somewhere"},
        {"capacity": "-1", "capacity_unit": "GWh/year"},
        {"value": "3"},
        {"currency": "XXX"},
        {"project_status": "operating"},
        {"evidence_quote": "not in original", "project_status": "announced"},
        {
            "value": "5",
            "unit": "EUR/litre",
            "currency": "USD",
            "price_type": "observed_price",
            "evidence_quote": "DEMO fictional",
        },
        {"planned_start": "2028-99-01"},
        {"url": "http://localhost/internal"},
        {"url": "https://user:password@official.test/"},
        {"capacity_unit": "GWh"},
    ],
)
def test_normalization_rejects_bad_claims(overrides):
    with pytest.raises(ValueError):
        record(**overrides)


def test_dates_aliases_and_evidence_no_capacity_promotion(factory):
    r = record(
        country="德国",
        company="宁德时代",
        capacity=Decimal("10"),
        capacity_unit="GWh/year",
        project_status="announced",
        evidence_quote="DEMO fictional",
    )
    assert r.country == "DE" and r.published_at.utcoffset().total_seconds() == 0
    with factory.begin() as s:
        register(s, [source()])
        ingest(s, "approved", r, now=NOW)
        result = rows(s, "demo")[0]
        assert result["raw"]["company"] == "CATL"
        assert result["raw"]["project_status"] == "announced"
        original = json.loads(s.scalar(select(Evidence)).raw_json)
        assert original["company"] == "宁德时代"


def test_risk_history_negation_future_not_current():
    assert assess(record(), NOW)["risk_level"] == "medium"
    assert assess(record(published_at=NOW - timedelta(days=31)), NOW)["risk_level"] == "unknown"
    assert assess(record(title="DEMO neutral", body="No strike is planned."), NOW)["risk_level"] == "unknown"
    assert assess(record(published_at=None), NOW)["risk_level"] == "unknown"
    assert assess(record(published_at=NOW + timedelta(days=10)), NOW)["risk_level"] == "unknown"


def test_csv_manual_isolation_per_row_errors(factory):
    r = record().model_dump(mode="json")
    r.update(
        external_id="manual-1",
        title="Manual historical notice",
        mode="manual",
        verification="MANUAL",
        url="https://official.test/news/1",
    )
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(r))
    writer.writeheader()
    writer.writerow(r)
    bad = {**r, "external_id": "bad", "mode": "live"}
    writer.writerow(bad)
    result = import_file(factory, out.getvalue().encode(), "input.csv")
    assert result["writes"] == {"inserted": 1} and len(result["errors"]) == 1
    assert import_file(factory, out.getvalue().encode(), "input.csv")["writes"] == {"unchanged": 1}
    with factory() as s:
        assert len(rows(s, "manual")) == 1 and not rows(s, "live") and not rows(s, "demo")


def test_excel_import_formula_and_empty_csv(factory):
    from openpyxl import Workbook

    w = Workbook()
    w.active.append(["external_id", "title"])
    w.active.append(["id", "=1+1"])
    b = io.BytesIO()
    w.save(b)
    with pytest.raises(ValueError, match="formulas"):
        import_file(factory, b.getvalue(), "data.xlsx")
    with pytest.raises(ValueError):
        import_file(factory, b"x" * 2_000_001, "data.csv")
    with pytest.raises(ValueError):
        import_file(factory, b"", "empty.csv")


@pytest.mark.parametrize(
    "adapter,content,mime",
    [
        ("rss", b"<rss><channel></channel></rss>", "application/rss+xml"),
        ("atom", b'<feed xmlns="http://www.w3.org/2005/Atom"></feed>', "application/atom+xml"),
        ("json_api", b'{"bad": []}', "application/json"),
        ("pdf_document", b"<html>Error</html>", "text/html"),
        ("html_document", b"<html>Shell</html>", "text/html"),
    ],
)
def test_adapter_failed_empty_never_success(factory, adapter, content, mime):
    def handler(request):
        return (
            httpx.Response(200, text="User-agent: *\nAllow: /")
            if request.url.path == "/robots.txt"
            else httpx.Response(200, content=content, headers={"content-type": mime})
        )

    fetcher = SafeFetcher(client=httpx.Client(transport=httpx.MockTransport(handler)), interval=0, retries=0)
    result = collect(factory, [source(adapter=adapter)], fetcher)[0]
    assert result["status"] == "failed" and not result["writes"]


def test_demo_fixture_explicit_optin(factory):
    from scm.platform.demo import seed

    assert seed(factory)["inserted"] == 5
    assert seed(factory)["unchanged"] == 5
    with factory() as s:
        assert not rows(s, "live")
        assert len(rows(s, "demo")) == 5
        assert generate_report(s, "live", day=NOW).html.find("DEMO factory") < 0
        assert (ROOT / "config/platform_import.template.csv").exists()


@pytest.mark.parametrize("adapter", ["rss", "atom", "json_api", "html_document", "pdf_document"])
def test_adapter_valid_contracts_stay_demo(factory, adapter):
    text = "DEMO fictional battery factory project delayed construction. This synthetic announcement is not live production. "
    html = "<h1>DEMO battery project</h1><article><p>" + text * 2 + "</p></article>"
    if adapter == "rss":
        content = b'<rss version="2.0"><channel><item><title>DEMO</title><link>https://official.test/news/1</link></item></channel></rss>'
        mime = "application/rss+xml"
    elif adapter == "atom":
        content = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>DEMO</title><link href="https://official.test/news/1"/></entry></feed>'
        mime = "application/atom+xml"
    elif adapter == "json_api":
        value = record(url="https://official.test/news/1").model_dump(mode="json")
        content = json.dumps({"records": [value]}).encode()
        mime = "application/json"
    elif adapter == "pdf_document":
        stream = f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET".encode()
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        ]
        pdf = b"%PDF-1.4\n"
        offsets = []
        for n, obj in enumerate(objects, 1):
            offsets.append(len(pdf))
            pdf += f"{n} 0 obj\n".encode() + obj + b"\nendobj\n"
        xref = len(pdf)
        pdf += (
            b"xref\n0 6\n0000000000 65535 f \n"
            + b"".join(f"{n:010d} 00000 n \n".encode() for n in offsets)
            + f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
        )
        content = pdf
        mime = "application/pdf"
    else:
        content = html.encode()
        mime = "text/html"

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.url.path == "/news/1":
            return httpx.Response(200, text=html, headers={"content-type": "text/html"})
        return httpx.Response(200, content=content, headers={"content-type": mime})

    fetcher = SafeFetcher(client=httpx.Client(transport=httpx.MockTransport(handler)), interval=0, retries=0)
    result = collect(factory, [source(adapter=adapter, document_title="DEMO synthetic PDF")], fetcher)[0]
    assert result["writes"] == {"inserted": 1}, result
    with factory() as s:
        assert len(rows(s, "demo")) == 1 and not rows(s, "live")


def test_review_rejection_reports_escape_and_version_scope(factory):
    with factory.begin() as s:
        register(s, [source()])
        _, item = ingest(s, "approved", record(title="DEMO <script>alert(1)</script>"), now=NOW)
        assert "<script>" not in generate_report(s, "demo", day=NOW).html
        review(s, item.id, "demo", "rejected", "synthetic rejection", "tester")
        assert "alert(1)" not in generate_report(s, "demo", day=NOW).html
        with pytest.raises(ValueError):
            review(s, item.id, "live", "confirmed", "wrong space", "tester")
        assert not rows(s, "live")


def test_manual_xlsx_valid(factory):
    from openpyxl import Workbook

    r = record().model_dump(mode="json")
    r.update(
        external_id="manual-xlsx",
        mode="manual",
        verification="MANUAL",
        title="Manual battery notice",
        url="https://official.test/news/1",
    )
    w = Workbook()
    w.active.append(list(r))
    w.active.append([json.dumps(v) if isinstance(v, dict) else v for v in r.values()])
    buffer = io.BytesIO()
    w.save(buffer)
    assert import_file(factory, buffer.getvalue(), "data.xlsx")["writes"] == {"inserted": 1}


def test_raw_http_capture_is_content_addressed_and_never_shared_modes(tmp_path):
    from scm.platform.capture import RecordingFetcher

    inner = SafeFetcher(
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    text="User-agent: *\nAllow: /"
                    if request.url.path == "/robots.txt"
                    else "<html>DEMO approved text</html>",
                )
            )
        ),
        interval=0,
        retries=0,
    )
    recorder = RecordingFetcher(inner, tmp_path)
    response = recorder.get("https://official.test/news/1")
    capture = recorder.captures[0]
    assert (
        capture["mode"] == "demo"
        and capture["sha256"] == __import__("hashlib").sha256(response.content).hexdigest()
    )
    assert (tmp_path / capture["path"]).read_bytes() == response.content
    recorder.get("https://official.test/news/1")
    assert recorder.captures[1]["path"] == capture["path"]
    (tmp_path / capture["path"]).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        recorder.get("https://official.test/news/1")


def test_current_view_expires_without_overwriting_original_analysis(factory, monkeypatch):
    from scm.platform import service
    from scm.platform.models import Assessment

    with factory.begin() as s:
        register(s, [source()])
        ingest(s, "approved", record(), now=NOW)
        original = s.scalar(select(Assessment)).payload_json
        monkeypatch.setattr(service, "utcnow", lambda: NOW + timedelta(days=31))
        assert rows(s, "demo")[0]["analysis"]["risk_level"] == "unknown"
        assert s.scalar(select(Assessment)).payload_json == original


def test_monetary_observation_requires_currency():
    with pytest.raises(ValueError, match="currency"):
        record(
            module="market",
            value="2",
            unit="EUR/litre",
            price_type="observed_price",
            evidence_quote="DEMO fictional",
        )
