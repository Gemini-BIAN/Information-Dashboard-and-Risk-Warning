"""Permission gates and explicit adapters, with per-source/per-record failure isolation."""

import csv
import hashlib
import io
import zipfile
from collections import Counter
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from scm.collectors.http import AccessBlocked, SafeFetcher
from scm.collectors.parsers import parse_article
from scm.collectors.service import collect_one, safe_error
from scm.platform.capture import RecordingFetcher
from scm.platform.contracts import Record
from scm.platform.models import PlatformSource
from scm.platform.service import audit, ingest, register, specs
from scm.settings import utcnow


def permission_gate(spec, now):
    policy = spec.get("reuse_policy", {})
    if (
        not spec.get("enabled")
        or not spec.get("automatic_access_allowed")
        or policy.get("status") != "reviewed_allowed"
        or policy.get("permission") != "allowed_full_text"
    ):
        raise AccessBlocked("NEEDS_PERMISSION: automatic access/text reuse not approved; zero requests")
    stamp = datetime.fromisoformat(policy.get("verified_at", "1900-01-01T00:00:00+00:00"))
    if (
        stamp.tzinfo is None
        or not now - timedelta(days=30) <= stamp <= now
        or not all(policy.get(k) for k in ["notice_url", "evidence_ref", "license"])
    ):
        raise AccessBlocked("NEEDS_PERMISSION: missing/expired rights evidence (30 days)")
    p = urlsplit(spec["url"])
    if p.scheme != "https" or not p.hostname or p.username or p.password or p.port not in [None, 443]:
        raise AccessBlocked("Unsupported source URL")


def _record(spec, title, body, url, published, verification, external_id=None):
    demo = verification != "LIVE_HTTP"
    return Record(
        external_id=("DEMO-" if demo else "") + (external_id or hashlib.sha256(url.encode()).hexdigest()),
        module=spec["module"],
        title=("DEMO · " if demo else "") + title,
        body=body,
        url=url,
        published_at=published,
        fetched_at=utcnow(),
        mode="demo" if demo else "live",
        verification="DEMO" if demo else "LIVE_HTTP",
    )


def fetch_records(spec, fetcher):
    adapter = spec["adapter"]
    if adapter in ["html_list", "rss", "atom"]:
        configured = {**spec, "method": "rss" if adapter in ["rss", "atom"] else "html"}
        articles, details = collect_one(configured, fetcher)
        return [
            _record(spec, a.title, a.body, str(a.url), a.published_at, fetcher.verification_type)
            for a in articles
        ], details
    response = fetcher.get(spec["url"])
    mime = response.headers.get("content-type", "").split(";")[0]
    if adapter == "json_api":
        if mime not in ["application/json", "application/geo+json"]:
            raise ValueError("API did not return JSON")
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
            raise ValueError("API requires object.records[] contract; no guessed schema")
        records = []
        errors = []
        for raw in payload["records"][:20]:
            try:
                value = Record.model_validate(
                    {
                        **raw,
                        "module": spec["module"],
                        "mode": "live" if fetcher.verification_type == "LIVE_HTTP" else "demo",
                        "verification": "LIVE_HTTP" if fetcher.verification_type == "LIVE_HTTP" else "DEMO",
                        "fetched_at": utcnow(),
                    }
                )
                if urlsplit(value.url).hostname != urlsplit(spec["url"]).hostname:
                    raise ValueError("API evidence link on unapproved host")
                records.append(value)
            except Exception as exc:
                errors.append({"error": safe_error(exc)})
        return records, {"article_errors": errors, "http_status": response.status_code}
    if adapter == "html_document":
        if mime != "text/html":
            raise ValueError("Expected HTML document")
        a = parse_article(response.text, spec["url"], spec.get("parser", "generic"))
        return [
            _record(spec, a["title"], a["body"], a["url"], a["published_at"], fetcher.verification_type)
        ], {}
    if adapter == "pdf_document":
        if (
            mime != "application/pdf"
            or not response.content.startswith(b"%PDF-")
            or b"%%EOF" not in response.content[-2048:]
        ):
            raise ValueError("Not an actual PDF; no error-page acceptance")
        from pypdf import PdfReader

        pdf = PdfReader(io.BytesIO(response.content), strict=True)
        body = "\n".join(p.extract_text() or "" for p in pdf.pages)
        if not body.strip() or len(body) > 200000:
            raise ValueError("Empty/scanned/oversized PDF needs manual processing")
        # Metadata is supplied by the reviewed source, never guessed from filenames.
        title = spec["document_title"]
        return [_record(spec, title, body, spec["url"], None, fetcher.verification_type)], {
            "quality_flags": ["PDF_LAYOUT_UNVERIFIED", "DATE_UNKNOWN"]
        }
    raise ValueError("Unsupported adapter; no fallback scraping")


def collect(factory, configurations=None, fetcher=None):
    owned = fetcher is None
    fetcher = RecordingFetcher(fetcher or SafeFetcher(retries=0))
    results = []
    selected = configurations if configurations is not None else specs()
    try:
        with factory.begin() as session:
            register(session, selected)
        for spec in selected:
            started = fetcher.request_count
            capture_start = len(fetcher.captures)
            result = {
                "source": spec["id"],
                "status": "failed",
                "mode": "live" if fetcher.verification_type == "LIVE_HTTP" else "demo",
                "stage": "permission",
                "writes": {},
                "automatic_retries": 0,
                "verification_type": fetcher.verification_type,
                "checked_at": utcnow().isoformat(),
            }
            try:
                permission_gate(spec, utcnow())
                result["stage"] = "robots_fetch_parse"
                records, details = fetch_records(spec, fetcher)
                counts = Counter()
                errors = details.get("article_errors", [])
                with factory.begin() as session:
                    for record in records:
                        try:
                            with session.begin_nested():
                                outcome, _ = ingest(session, spec["id"], record)
                                counts[outcome] += 1
                        except Exception as exc:
                            errors.append({"error": safe_error(exc)})
                result.update(
                    writes=dict(counts),
                    status="candidate" if sum(counts.values()) else "failed",
                    stage="stored"
                    if sum(counts.values())
                    else details.get("failure_stage") or "parse_or_store",
                    details=details,
                    errors=errors,
                )
            except Exception as exc:
                result["error"] = safe_error(exc)
                if isinstance(exc, AccessBlocked):
                    result["status"] = "unavailable"
            result["captures"] = fetcher.captures[capture_start:]
            result["requests"] = fetcher.request_count - started
            result["robots"] = dict(fetcher.robots_audit)
            with factory.begin() as session:
                source = session.get(PlatformSource, spec["id"])
                if result["mode"] == "live":
                    source.last_checked_at = result["checked_at"]
                    source.status = result["status"]
                    if sum(result["writes"].values()):
                        source.last_success_at = result["checked_at"]
                audit(session, spec["id"], result["mode"], result)
            results.append(result)
    finally:
        if owned:
            fetcher.close()
    return results


def import_file(factory, content, filename):
    if len(content) > 2_000_000:
        raise ValueError("Import exceeds 2MB")
    if filename.lower().endswith(".csv"):
        raw = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    elif filename.lower().endswith(".xlsx"):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(z.file_size for z in archive.infolist()) > 20_000_000:
                raise ValueError("Excel decompression limit exceeded")
        from openpyxl import load_workbook

        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        cells = workbook.active.iter_rows(values_only=False)
        header = [c.value for c in next(cells)]
        raw = []
        for line in cells:
            if any(c.data_type == "f" for c in line):
                workbook.close()
                raise ValueError("Excel formulas are not accepted")
            raw.append(dict(zip(header, [c.value for c in line], strict=True)))
        workbook.close()
    else:
        raise ValueError("CSV/XLSX only")
    if len(raw) > 1000 or not raw:
        raise ValueError("Import requires 1–1000 rows")
    counts = Counter()
    errors = []
    with factory.begin() as session:
        register(
            session,
            [
                {
                    "id": "manual-import",
                    "name": "Manual user supplied, not verified",
                    "adapter": "manual",
                    "url": "https://example.invalid/manual",
                    "automatic_access_allowed": False,
                }
            ],
        )
        for number, row in enumerate(raw, 2):
            try:
                if row.get("mode") not in [None, "", "manual"] or row.get("verification") not in [
                    None,
                    "",
                    "MANUAL",
                ]:
                    raise ValueError("Manual import cannot set Live/DEMO provenance")
                cleaned = {k: v for k, v in row.items() if v not in [None, ""]}
                rec = Record.model_validate(
                    {**cleaned, "mode": "manual", "verification": "MANUAL", "fetched_at": utcnow()}
                )
                with session.begin_nested():
                    outcome, _ = ingest(session, "manual-import", rec)
                    counts[outcome] += 1
            except Exception as exc:
                errors.append({"row": number, "error": safe_error(exc)})
        audit(session, "manual-import", "manual", {"writes": dict(counts), "errors": errors})
    return {"writes": dict(counts), "errors": errors}
