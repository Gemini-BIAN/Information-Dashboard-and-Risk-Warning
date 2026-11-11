"""Verify actual locally acquired law, citations and byte provenance. Never seeds/downloads fixtures."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import select

from scm.database.session import session_factory
from scm.regulatory.manifest import ManifestEntry
from scm.regulatory.models import RegulationChunk, RegulationDocument
from scm.regulatory.parsing import parse_document
from scm.regulatory.retrieval import answer
from scm.regulatory.storage import checked_path, validate_pdf_identity
from scm.regulatory.work import read_work
from scm.settings import ROOT, utcnow


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database-url", default="sqlite:///runtime/regulatory/library.db")
    p.add_argument("--storage", type=Path, default=ROOT / "runtime/regulatory/files")
    p.add_argument("--research", type=Path, default=ROOT / "data/regulatory/research")
    p.add_argument("--output", type=Path, default=ROOT / "docs/regulatory/LIVE_EVIDENCE.json")
    args = p.parse_args()
    work = read_work(args.research)
    assert len(work["catalog"]) == 57 and len(work["manifest"]) == 18
    assert Counter(c["优先级"] for c in work["catalog"]) == {"P0": 18, "P1": 31, "P2": 8}
    factory = session_factory(args.database_url)
    report = {
        "verified_at": utcnow().isoformat(),
        "verification_type": "ACTUAL_LOCAL_BYTES_FROM_LIVE_HTTP",
        "input_files": work["files"],
        "candidate_counts": {
            "master": 57,
            "P0_manifest": 18,
            "research_title_link_reviewed": 9,
            "research_candidate": 48,
        },
        "documents": [],
        "queries": [],
        "real_regulations": 0,
        "real_files": 0,
        "no_llm": True,
    }
    with factory.begin() as session:
        rows = list(session.scalars(select(RegulationDocument)))
        downloaded = [
            r for r in rows if r.download_status == "downloaded" and r.verification_type == "LIVE_HTTP"
        ]
        for row in downloaded:
            path = checked_path(row, args.storage)
            reader = PdfReader(path)
            validate_pdf_identity(path.read_bytes(), ManifestEntry.model_validate_json(row.metadata_json))
            result = parse_document(session, row, args.storage)
            assert result["chunks"] > 0 and result["parse_status"] != "failed"
            meta = json.loads(row.metadata_json)
            assert meta["legal_status"] == "unknown" and meta["verification_status"] == "pending"
            assert meta["source_evidence"]["identity_checked"]
            units = list(
                session.scalars(select(RegulationChunk).where(RegulationChunk.document_id == row.id))
            )
            report["documents"].append(
                {
                    "document_id": row.id,
                    "celex": meta["celex"],
                    "regulation_number": meta["regulation_number"],
                    "version_kind": meta["version_kind"],
                    "version_date": meta.get("version_date"),
                    "publication_date": meta.get("publication_date"),
                    "download_url": meta["download_url"],
                    "official_url": meta["official_url"],
                    "downloaded_at": row.downloaded_at,
                    "local_path": str(path.relative_to(ROOT)),
                    "sha256": row.sha256,
                    "actual_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "byte_size": row.byte_size,
                    "pdf_pages": len(reader.pages),
                    "chunks": len(units),
                    "articles": len({c.unit_label for c in units if c.unit_type == "article"}),
                    "annexes": len({c.unit_label for c in units if c.unit_type == "annex"}),
                    "parse_status": row.parse_status,
                    "quality_flags": json.loads(row.quality_json),
                    "legal_status": "unknown",
                    "verification_status": "pending",
                    "source_evidence": meta["source_evidence"],
                    "strict_formal_heading_verified": True,
                    "index_unchanged": result["index_unchanged"],
                }
            )
        primary = next(r for r in downloaded if json.loads(r.metadata_json)["celex"] == "32023R1542")
        pdf = PdfReader(checked_path(primary, args.storage))
        for question, unit, label, pages in [
            ("Regulation (EU) 2023/1542 Article 7 对碳足迹有什么要求？", "article", "7", [31, 32, 33]),
            ("Annex I 附件 I 限制物质有哪些？", "annex", "I", [84]),
        ]:
            result = answer(session, question, primary.id, args.storage)
            assert result["evidence"] and all(
                e["unit_type"] == unit and e["unit_label"] == label for e in result["evidence"]
            )
            checked = []
            for e in result["evidence"]:
                text = "\n".join(
                    pdf.pages[i - 1].extract_text() or "" for i in range(e["page_start"], e["page_end"] + 1)
                )
                assert re.sub(r"\s+", " ", e["quote"]).strip() in re.sub(r"\s+", " ", text)
                assert e["page_start"] in pages and e["page_end"] in pages
                assert e["source_sha256"] == primary.sha256 and e["document_id"] == primary.id
                checked.append(
                    {
                        k: e[k]
                        for k in [
                            "document_id",
                            "chunk_id",
                            "celex",
                            "unit_type",
                            "unit_label",
                            "page_start",
                            "page_end",
                            "locator",
                            "quote",
                            "citation_url",
                            "source_sha256",
                        ]
                    }
                )
            report["queries"].append(
                {
                    "question": question,
                    "status": "PASS",
                    "quote_checked_against_reopened_pdf": True,
                    "evidence": checked,
                }
            )
        for question in [
            "REACH 与 CLP 分别有什么要求？",
            "ISO Tank 在欧洲运输需核查哪些危险品规则？",
            "目前Article 7碳足迹适用要求？",
        ]:
            assert not answer(session, question, primary.id, args.storage)["evidence"]
        consolidated = next(r for r in rows if json.loads(r.metadata_json)["celex"] == "02023R1542-20260813")
        assert consolidated.id != primary.id
        assert not answer(session, "Article 7碳足迹", consolidated.id, args.storage)["evidence"]
        report["version_isolation"] = {
            "status": "PASS",
            "original_id": primary.id,
            "consolidated_id": consolidated.id,
            "consolidated_download_status": consolidated.download_status,
            "consolidated_parse_status": consolidated.parse_status,
            "note": "Candidate consolidated URL returned HTML, not PDF; no original chunks borrowed.",
        }
        report["negative_queries"] = (
            "PASS: scoped other-law/ISO Tank/current-law questions refuse unsupported conclusions"
        )
        report["real_regulations"] = len({json.loads(r.metadata_json)["celex"] for r in downloaded})
        report["real_files"] = len({r.sha256 for r in downloaded})
        report["not_downloaded_targets"] = len(rows) - len(downloaded)
        # Re-import and hash-checked safe rerun must preserve records, dates and byte evidence.
        from scm.regulatory.storage import download
        from scm.regulatory.work import import_work

        before = {r.id: (r.sha256, r.download_status) for r in rows}
        import_work(session, args.research, ROOT / "runtime/regulatory/research-snapshot.json")
        assert before == {
            r.id: (r.sha256, r.download_status) for r in session.scalars(select(RegulationDocument))
        }
        policy = json.loads((ROOT / "config/regulatory/permissions.json").read_text())
        repeat = download(
            session, ManifestEntry.model_validate_json(primary.metadata_json), args.storage, policy
        )
        assert repeat["status"] == "UNCHANGED"
        report["safe_rerun"] = {
            "status": "PASS",
            "repeat_download": repeat,
            "records_before_after": len(rows),
            "note": "Local hash verified; no duplicate or legal-status promotion on research re-import",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "real_files": report["real_files"],
                "real_regulations": report["real_regulations"],
                "documents": [
                    (d["celex"], d["chunks"], d["articles"], d["annexes"]) for d in report["documents"]
                ],
                "query_checks": "PASS",
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
