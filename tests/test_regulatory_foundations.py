"""All legal content here is synthetic. These tests are not a real-law RAG acceptance."""

import io
from datetime import timedelta

import httpx
import pytest
from openpyxl import Workbook
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import func, select

from scm.collectors.http import SafeFetcher
from scm.regulatory.manifest import ManifestEntry, input_status, load_manifest
from scm.regulatory.models import RegulationAttempt, RegulationChunk, RegulationDocument
from scm.regulatory.parsing import parse_document
from scm.regulatory.retrieval import answer
from scm.regulatory.storage import checked_path, download, register, validate_bytes
from scm.settings import utcnow

HTML = b"""<!doctype html><html><body><article><h2>Article 7</h2><h3>Synthetic carbon footprint</h3><p>Synthetic only: carbon footprint evidence is recorded for this test.</p><h2>ANNEX I</h2><table><tr><td>Synthetic annex table only.</td></tr></table></article></body></html>"""


def entry(**patch):
    data = dict(
        regulation_number="SYNTHETIC 2000/0",
        title="Synthetic test only",
        celex="32000R0000",
        official_url="https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32000R0000",
        download_url="https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32000R0000",
        language="EN",
        version_kind="official",
        format="html",
        priority="P2",
    )
    return ManifestEntry(**(data | patch))


def permissions():
    return {
        "sources": [
            {
                "host": "eur-lex.europa.eu",
                "automated_access": True,
                "text_retention": True,
                "evidence_ref": "SYNTHETIC TEST POLICY ONLY",
                "license": "synthetic permission",
                "notice_url": "https://eur-lex.europa.eu/legal-notice",
                "verified_at": utcnow().isoformat(),
            }
        ]
    }


def mock_fetcher(body=HTML, content_type="text/html", status=200):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(status, content=body, headers={"Content-Type": content_type})

    return SafeFetcher(httpx.Client(transport=httpx.MockTransport(handler)), interval=0, retries=0), calls


def test_missing_inputs_and_empty_template_fail_truthfully(tmp_path):
    assert len(input_status(tmp_path)) == 5 and not any(x["present"] for x in input_status(tmp_path))
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / "absent.csv")
    path = tmp_path / "empty.csv"
    path.write_text("regulation_number,title\n")
    with pytest.raises(ValueError, match="Empty manifest"):
        load_manifest(path)


@pytest.mark.parametrize(
    "patch",
    [
        {"download_url": "https://other.test/legal.pdf"},
        {"download_url": "https://eur-lex.europa.eu/?token=secret"},
        {"download_url": "https://name:password@eur-lex.europa.eu/file"},
        {"celex": "32023R1542"},
        {"version_kind": "consolidated"},
        {"celex": "02000R0000-20200101", "version_kind": "consolidated", "version_date": "2020-02-01"},
        {"legal_status": "effective"},
    ],
)
def test_manifest_identity_and_legal_unknowns(patch):
    with pytest.raises(ValueError):
        entry(**patch)


def test_xlsx_normalized_import_and_duplicate_rejection(tmp_path):
    e = entry()
    values = e.model_dump(mode="json", exclude_none=True)
    book = Workbook()
    sheet = book.active
    sheet.append(list(values))
    sheet.append(list(values.values()))
    path = tmp_path / "normalized.xlsx"
    book.save(path)
    book.close()
    assert load_manifest(path)[0].identity() == e.identity()
    book = Workbook()
    sheet = book.active
    sheet.append(list(values))
    sheet.append(list(values.values()))
    sheet.append(list(values.values()))
    book.save(path)
    book.close()
    with pytest.raises(ValueError, match="Duplicate document"):
        load_manifest(path)


def test_permission_gate_has_zero_http_and_never_marks_downloaded(factory, tmp_path):
    f, calls = mock_fetcher()
    with factory.begin() as session:
        result = download(session, entry(), tmp_path, {"sources": []}, f)
        assert result["status"] == "BLOCKED" and not calls
        assert session.get(RegulationDocument, entry().identity()).download_status == "blocked"
        assert session.scalar(select(func.count(RegulationAttempt.id))) == 1
    f.close()


@pytest.mark.parametrize(
    "body,mime,status",
    [
        (b"<html>captcha</html>", "application/pdf", 200),
        (b"%PDF-1.7 broken", "application/pdf", 200),
        (HTML, "application/pdf", 200),
        (HTML, "text/html", 202),
    ],
)
def test_wrong_bytes_or_partial_response_not_success(factory, tmp_path, body, mime, status):
    f, _ = mock_fetcher(body, mime, status)
    e = entry(format="pdf") if mime == "application/pdf" else entry()
    with factory.begin() as session:
        result = download(session, e, tmp_path, permissions(), f)
        assert result["status"] == "BLOCKED" and session.get(
            RegulationDocument, e.identity()
        ).download_status == ("blocked" if b"captcha" in body else "failed")
    assert not list(tmp_path.rglob("*.part"))
    f.close()


def test_synthetic_end_to_end_version_scoped_quotes_and_no_live_promotion(factory, tmp_path):
    f, calls = mock_fetcher()
    e = entry()
    with factory.begin() as session:
        first = download(session, e, tmp_path, permissions(), f)
        assert first["status"] == "PASS" and first["verification_type"] == "INJECTED_TEST_CLIENT"
        assert download(session, e, tmp_path, permissions(), f)["status"] == "UNCHANGED"
        assert len(calls) == 2
        row = session.get(RegulationDocument, e.identity())
        path = checked_path(row, tmp_path)
        result = parse_document(session, row, tmp_path)
        assert result["parse_status"] == "needs_review"
        assert "TABLE_REQUIRES_REVIEW" in result["flags"]
        chunks = list(session.scalars(select(RegulationChunk).where(RegulationChunk.document_id == row.id)))
        assert {c.unit_type for c in chunks} == {"article", "annex"}
        assert all(c.page_start is None for c in chunks)
        parsed = answer(session, "Article 7 对碳足迹有什么要求？", row.id, tmp_path, include_test=True)
        assert parsed["evidence"][0]["unit_label"] == "7"
        assert parsed["evidence"][0]["quote"].startswith("Article\n7") is False
        assert "Synthetic only" in parsed["evidence"][0]["quote"]
        assert parsed["evidence"][0]["celex"] == e.celex
        assert parsed["evidence"][0]["legal_status"] == "unknown"
        assert not answer(session, "碳足迹", row.id, tmp_path)["evidence"]
        assert not answer(session, "REACH与CLP分别有什么要求", row.id, tmp_path, include_test=True)[
            "evidence"
        ]
        assert not answer(
            session, "ISO Tank在欧洲运输需核查什么危险品规则", row.id, tmp_path, include_test=True
        )["evidence"]
        assert not answer(session, "Article 70 碳足迹", row.id, tmp_path, include_test=True)["evidence"]
        consolidated = entry(
            celex="02000R0000-20200101",
            version_kind="consolidated",
            version_date="2020-01-01",
            download_url="https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02000R0000-20200101",
        )
        download(session, consolidated, tmp_path, permissions(), f)
        other = session.get(RegulationDocument, consolidated.identity())
        parse_document(session, other, tmp_path)
        assert other.id != row.id and other.local_path == row.local_path  # byte dedup, metadata isolation
        refs = answer(session, "Article 7 碳足迹", other.id, tmp_path, include_test=True)["evidence"]
        assert all(r["celex"] == consolidated.celex and r["document_id"] == other.id for r in refs)
        path.write_bytes(b"corrupt")
        assert not answer(session, "碳足迹", row.id, tmp_path, include_test=True)["evidence"]
        assert download(session, e, tmp_path, permissions(), f)["status"] == "PASS"
        assert checked_path(row, tmp_path).read_bytes() == HTML
    f.close()


def synthetic_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 14 TL 72 720 Td (Article 7) Tj T* (Synthetic carbon footprint text only.) Tj T* (ANNEX I) Tj T* (Synthetic annex content only.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    out = io.BytesIO()
    writer.write(out)
    writer.close()
    return out.getvalue()


def test_generated_pdf_validation_and_reliable_page_range(factory, tmp_path):
    data = synthetic_pdf()
    assert len(validate_bytes(data, "application/pdf", "pdf")) == 64
    f, _ = mock_fetcher(data, "application/pdf")
    e = entry(format="pdf")
    with factory.begin() as session:
        download(session, e, tmp_path, permissions(), f)
        row = session.get(RegulationDocument, e.identity())
        parsed = parse_document(session, row, tmp_path)
        assert parsed["chunks"] == 2 and "PDF_LAYOUT_REQUIRES_REVIEW" in parsed["flags"]
        chunks = list(session.scalars(select(RegulationChunk).where(RegulationChunk.document_id == row.id)))
        assert all(c.page_start == 1 and c.page_end == 1 for c in chunks)
    f.close()


def test_parse_failure_and_undownloaded_document_never_cited(factory, tmp_path):
    with factory.begin() as session:
        row = register(session, entry())
        with pytest.raises(ValueError):
            parse_document(session, row, tmp_path)
        assert not answer(session, "碳足迹", row.id, tmp_path)["evidence"]
    empty_writer = PdfWriter()
    empty_writer.add_blank_page(width=100, height=100)
    out = io.BytesIO()
    empty_writer.write(out)
    f, _ = mock_fetcher(out.getvalue(), "application/pdf")
    e = entry(format="pdf")
    with factory.begin() as session:
        download(session, e, tmp_path, permissions(), f)
        row = session.get(RegulationDocument, e.identity())
        result = parse_document(session, row, tmp_path)
        assert result["parse_status"] == "failed" and not result["chunks"]
        assert not answer(session, "Article 7", row.id, tmp_path, include_test=True)["evidence"]
    f.close()


def test_xml_entity_rejected_and_permission_expiry(factory, tmp_path):
    with pytest.raises(ValueError):
        validate_bytes(b'<!DOCTYPE x [<!ENTITY v SYSTEM "file:///etc/passwd">]><x>&v;</x>', "text/xml", "xml")
    f, calls = mock_fetcher()
    p = permissions()
    p["sources"][0]["verified_at"] = (utcnow() - timedelta(days=31)).isoformat()
    with factory.begin() as s:
        assert download(s, entry(), tmp_path, p, f)["status"] == "BLOCKED"
    assert not calls
    f.close()
