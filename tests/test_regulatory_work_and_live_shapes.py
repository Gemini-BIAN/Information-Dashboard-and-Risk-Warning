"""Offline regressions for Work column mapping and actual PDF layout bugs. No real download counts."""

import csv

import pytest
from openpyxl import Workbook

from scm.regulatory.manifest import EXPECTED_FILES, input_status
from scm.regulatory.parsing import extract_chunks
from scm.regulatory.work import import_work, resolve_input


def write_book(path, headers, rows):
    book = Workbook()
    sheet = book.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    book.save(path)
    book.close()


def work_fixture(folder):
    folder.mkdir(exist_ok=True)
    columns = [
        "优先级",
        "主题",
        "法规/规则编号",
        "官方标题（EN）",
        "CELEX",
        "官方 ELI URL",
        "核实级别",
        "下载状态",
    ]
    write_book(
        folder / EXPECTED_FILES[0],
        columns,
        [
            [
                "P0",
                "电池",
                "SYNTHETIC 2000/0",
                "Synthetic test only",
                "32000R0000",
                None,
                "Candidate record; status/date needs validation",
                "LINK_ONLY_NOT_DOWNLOADED",
            ]
        ],
    )
    write_book(
        folder / EXPECTED_FILES[1], ["来源/渠道", "费用/许可"], [["Synthetic official", "NOT REVIEWED"]]
    )
    for name in EXPECTED_FILES[2:4]:
        (folder / name).write_text("# Synthetic document, not actual Work evidence\n")
    with (folder / "EU_Regulation_Download_Manifest(1).csv").open("w", newline="") as stream:
        columns = [
            "act_number",
            "priority",
            "celex",
            "document_type",
            "language",
            "official_url",
            "original_pdf_url",
            "consolidated_url",
            "download_status",
        ]
        writer = csv.DictWriter(stream, columns)
        writer.writeheader()
        writer.writerow(
            dict(
                act_number="SYNTHETIC 2000/0",
                priority="P0",
                celex="32000R0000",
                document_type="Regulation",
                language="EN",
                official_url="https://eur-lex.europa.eu/?uri=CELEX:32000R0000",
                original_pdf_url="https://eur-lex.europa.eu/file.pdf",
                consolidated_url="https://eur-lex.europa.eu/eli/reg/2000/0/2020-01-01/eng/pdf",
                download_status="LINK_ONLY_NOT_DOWNLOADED",
            )
        )


def test_work_variant_maps_candidate_and_versions_without_promoting_status(factory, tmp_path):
    directory = tmp_path / "research"
    work_fixture(directory)
    assert all(x["present"] for x in input_status(directory))
    with factory.begin() as s:
        snapshot = import_work(s, directory, tmp_path / "snapshot.json")
        assert snapshot["counts"]["catalog"] == 1 and snapshot["counts"]["manifest"] == 1
        assert snapshot["counts"]["normalized_document_targets"] == 2
        assert snapshot["catalog"][0]["核实级别"] == "Candidate record; status/date needs validation"
        import json

        from sqlalchemy import select

        from scm.regulatory.models import RegulationDocument

        rows = list(s.scalars(select(RegulationDocument)))
        assert len(rows) == 2 and all(r.download_status == "not_downloaded" for r in rows)
        assert all(json.loads(r.metadata_json)["legal_status"] == "unknown" for r in rows)
        assert all(json.loads(r.metadata_json)["verification_status"] == "pending" for r in rows)
        assert {json.loads(r.metadata_json)["celex"] for r in rows} == {"32000R0000", "02000R0000-20200101"}
    (directory / EXPECTED_FILES[-1]).write_text("conflicting content")
    with pytest.raises(ValueError, match="Different manifest"):
        resolve_input(directory, EXPECTED_FILES[-1])


def test_strict_heading_does_not_index_correlation_or_cross_reference_as_article():
    pages = [
        (
            31,
            "Article 7\nCarbon footprint\n1. Statement requires carbon footprint.\nArticle 90(3).\nContinued conditions.",
            [],
        ),
        (32, "2. More requirements.", []),
        (33, "\nArticle 8\nPerformance requirements.", []),
        (84, "ANNEX I\nRESTRICTION ON SUBSTANCES\nMercury conditions.", []),
        (85, "\nANNEX II\nCarbon footprint methodology.", []),
        (112, "ANNEX XV\nCORRELATION TABLE\nArticle 7  Article 2\nAnnex I  Annex XI", []),
    ]
    chunks = extract_chunks(pages)
    articles = [c for c in chunks if c["unit_type"] == "article" and c["unit_label"] == "7"]
    assert len(articles) == 1 and articles[0]["page_start"] == 31 and articles[0]["page_end"] == 32
    assert "Article 90(3)" in articles[0]["text"]
    annex = [c for c in chunks if c["unit_type"] == "annex" and c["unit_label"] == "I"]
    assert len(annex) == 1 and annex[0]["page_start"] == annex[0]["page_end"] == 84
    assert any("Article 7  Article 2" in c["text"] and c["unit_label"] == "XV" for c in chunks)


def test_chunk_partition_keeps_every_extracted_character_and_paragraphs():
    text = "Article 7\n1. " + ("Long legal conditions. " * 80) + "\n2. " + ("More conditions. " * 100)
    chunks = extract_chunks([(1, text, [])], max_chars=900)
    assert "".join(c["text"] for c in chunks) == text
    assert all(c["unit_label"] == "7" for c in chunks)


def test_regulatory_size_override_is_bounded_and_legacy_default_unchanged():
    import httpx

    from scm.collectors.http import AccessBlocked, SafeFetcher

    body = b"x" * 4_000_100

    def handler(request):
        return (
            httpx.Response(200, text="User-agent: *\nAllow: /")
            if request.url.path == "/robots.txt"
            else httpx.Response(200, content=body)
        )

    def client():
        return httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(AccessBlocked, match="4MB"):
        f = SafeFetcher(client(), interval=0, retries=0)
        try:
            f.get("https://eur-lex.europa.eu/file.pdf")
        finally:
            f.close()
    f = SafeFetcher(client(), interval=0, retries=0, max_bytes=32_000_000)
    try:
        assert len(f.get("https://eur-lex.europa.eu/file.pdf").content) == len(body)
    finally:
        f.close()
    with pytest.raises(ValueError):
        SafeFetcher(max_bytes=32_000_001)


def test_wrong_or_mock_pdf_cannot_pass_actual_legal_identity_check():
    from test_regulatory_foundations import entry, synthetic_pdf

    from scm.regulatory.storage import validate_pdf_identity

    with pytest.raises(ValueError, match="formal legal heading"):
        validate_pdf_identity(synthetic_pdf(), entry(format="pdf"))


def test_reparse_keeps_citation_ids_and_reimport_keeps_byte_provenance(factory, tmp_path):
    import json

    from sqlalchemy import select
    from test_regulatory_foundations import entry, mock_fetcher, permissions

    from scm.regulatory.models import RegulationChunk, RegulationDocument
    from scm.regulatory.parsing import parse_document
    from scm.regulatory.storage import download, register

    f, _ = mock_fetcher()
    e = entry()
    with factory.begin() as s:
        download(s, e, tmp_path, permissions(), f)
        row = s.get(RegulationDocument, e.identity())
        parse_document(s, row, tmp_path)
        ids = list(s.scalars(select(RegulationChunk.id).where(RegulationChunk.document_id == row.id)))
        assert parse_document(s, row, tmp_path)["index_unchanged"]
        assert list(s.scalars(select(RegulationChunk.id).where(RegulationChunk.document_id == row.id))) == ids
        metadata = json.loads(row.metadata_json)
        metadata["source_evidence"] = {"source_sha256": row.sha256, "identity_checked": True}
        metadata["publication_date"] = "2000-01-01"
        row.metadata_json = json.dumps(metadata)
        register(s, e)
        assert json.loads(row.metadata_json)["source_evidence"]["identity_checked"]
        assert json.loads(row.metadata_json)["publication_date"] == "2000-01-01"
        assert json.loads(row.metadata_json)["legal_status"] == "unknown"
    f.close()
