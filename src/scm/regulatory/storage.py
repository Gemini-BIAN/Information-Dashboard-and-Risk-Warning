import hashlib
import io
import json
import os
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from pypdf import PdfReader

from scm.collectors.http import AccessBlocked, SafeFetcher
from scm.regulatory.manifest import official_url
from scm.regulatory.models import RegulationAttempt, RegulationDocument
from scm.settings import utcnow


def validate_bytes(content, content_type, format):
    mime = content_type.split(";", 1)[0].strip().lower()
    accepted = {
        "pdf": {"application/pdf"},
        "html": {"text/html", "application/xhtml+xml"},
        "xml": {"application/xml", "text/xml"},
    }
    if mime not in accepted[format]:
        raise ValueError(f"Unexpected Content-Type for {format}: {mime}")
    if not content:
        raise ValueError("Empty response")
    if format == "pdf":
        if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-2048:]:
            raise ValueError("Invalid PDF header/trailer; possible HTML challenge")
        reader = PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted or not reader.pages:
            raise ValueError("Unreadable/encrypted PDF")
    else:
        text = content.decode("utf-8-sig")
        if any(
            term in text[:50000].lower() for term in ["captcha", "verify you are human", "just a moment..."]
        ):
            raise AccessBlocked("Challenge page; not a legal text")
        if format == "html":
            if not re.search(r"<(?:!doctype html|html)\b", text, re.I):
                raise ValueError("Missing HTML document header")
            soup = BeautifulSoup(text, "html.parser")
            if not (soup.find("article") or soup.find("main") or soup.select_one("#document1")):
                raise ValueError("No identifiable legal content container; possible login/listing shell")
        else:
            if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
                raise ValueError("XML DTD/entity unsupported; no external expansion")
            ElementTree.fromstring(text)
    return hashlib.sha256(content).hexdigest()


def permission_gate(entry, permissions, now):
    host = urlsplit(entry.download_url).hostname
    policy = next((p for p in permissions.get("sources", []) if p.get("host") == host), None)
    if not policy or policy.get("automated_access") is not True or policy.get("text_retention") is not True:
        raise AccessBlocked("NEEDS_PERMISSION: source-specific automatic access and reuse not reviewed")
    if not policy.get("evidence_ref") or not policy.get("license"):
        raise AccessBlocked("NEEDS_PERMISSION: no permission evidence/license")
    official_url(policy.get("notice_url", ""))
    verified = datetime.fromisoformat(policy.get("verified_at", ""))
    if verified.tzinfo is None or not now - timedelta(days=30) <= verified <= now:
        raise AccessBlocked("NEEDS_PERMISSION: permission review stale or undated")
    return policy


def register(session, entry):
    row = session.get(RegulationDocument, entry.identity())
    if row is None:
        row = RegulationDocument(
            id=entry.identity(),
            metadata_json=entry.model_dump_json(),
            download_status="not_downloaded",
            parse_status="not_parsed",
            quality_json="[]",
        )
        session.add(row)
        session.flush()
    else:
        # Version identity is immutable; metadata may update without erasing byte provenance.
        row.metadata_json = entry.model_dump_json()
    return row


def checked_path(row, root):
    root = Path(root).resolve()
    if not row.local_path:
        raise ValueError("No downloaded local file")
    path = (root / row.local_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Stored file missing or outside library")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != row.sha256 or len(content) != row.byte_size:
        raise ValueError("Stored file hash/size mismatch; safe re-download required")
    return path


def download(session, entry, root, permissions, fetcher=None):
    row = register(session, entry)
    audit = {"url": entry.download_url, "stage": "permission", "status": "BLOCKED", "http_status": None}
    owned = fetcher is None
    fetcher = fetcher or SafeFetcher(retries=1)
    try:
        policy = permission_gate(entry, permissions, utcnow())
        audit["permission_evidence"] = policy["evidence_ref"]
        if row.download_status == "downloaded" and row.verification_type == fetcher.verification_type:
            try:
                checked_path(row, root)
                audit.update(status="UNCHANGED", stage="verified_local_hash")
                return audit
            except ValueError:
                pass
        audit["stage"] = "robots_or_download"
        response = fetcher.get(entry.download_url)
        if response.status_code != 200:
            raise ValueError("Only complete HTTP200 responses are accepted; no partial file success")
        audit["http_status"] = response.status_code
        audit["stage"] = "byte_validation"
        content = response.content
        declared = response.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) != len(content):
            raise ValueError("Content-Length differs from decoded bytes")
        sha = validate_bytes(content, response.headers.get("content-type", ""), entry.format)
        root = Path(root).resolve()
        relative = Path("objects") / sha[:2] / (sha + "." + entry.format)
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.resolve().is_relative_to(root):
            raise ValueError("Object path outside library")
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != sha:
            quarantine = target.with_suffix(target.suffix + "." + uuid.uuid4().hex + ".corrupt")
            os.replace(target, quarantine)
            audit["quarantined_object"] = quarantine.relative_to(root).as_posix()
        temp = target.with_suffix(target.suffix + "." + uuid.uuid4().hex + ".part")
        try:
            if not target.exists():
                with temp.open("xb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
        if row.sha256 and row.sha256 != sha:
            row.parse_status = "not_parsed"
        row.sha256, row.byte_size, row.local_path = sha, len(content), relative.as_posix()
        row.download_status, row.downloaded_at, row.verification_type = (
            "downloaded",
            utcnow().isoformat(),
            fetcher.verification_type,
        )
        row.error = None
        audit.update(
            status="PASS",
            stage="stored",
            sha256=sha,
            byte_size=len(content),
            verification_type=fetcher.verification_type,
        )
        return audit
    except Exception as exc:
        # A failed attempt never validates the previously missing/corrupt file.
        row.download_status = "blocked" if isinstance(exc, AccessBlocked) else "failed"
        row.error = (
            type(exc).__name__
            + ": "
            + (str(exc)[:240] if isinstance(exc, (ValueError, AccessBlocked)) else "request/parse failed")
        )
        audit["error"] = row.error
        return audit
    finally:
        audit["robots"] = dict(fetcher.robots_audit)
        session.add(
            RegulationAttempt(
                document_id=row.id,
                attempted_at=utcnow().isoformat(),
                status=audit["status"],
                details_json=json.dumps(audit, ensure_ascii=False),
            )
        )
        if owned:
            fetcher.close()
