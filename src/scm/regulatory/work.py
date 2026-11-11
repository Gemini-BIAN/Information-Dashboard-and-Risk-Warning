"""Explicit mapping of the supplied Work deliverables. Raw evidence stays local/unchanged."""

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

from scm.regulatory.manifest import EXPECTED_FILES, ManifestEntry
from scm.regulatory.storage import register
from scm.settings import utcnow

CATALOG = "EU_Regulation_Master_Catalog.xlsx"
MANIFEST = "EU_Regulation_Download_Manifest.csv"


def resolve_input(directory, name):
    directory = Path(directory)
    paths = [directory / name]
    if name == MANIFEST:
        paths.append(directory / "EU_Regulation_Download_Manifest(1).csv")
    present = [p for p in paths if p.is_file()]
    if not present:
        raise FileNotFoundError(name)
    if len(present) > 1 and len({p.read_bytes() for p in present}) != 1:
        raise ValueError("Different manifest variants; cannot silently choose one")
    return present[0]


def workbook_rows(path):
    book = load_workbook(path, read_only=True, data_only=True)
    try:
        values = list(book.active.iter_rows(values_only=True))
        headers = values[0]
        if len(headers) != len(set(headers)):
            raise ValueError("Duplicate Work headers")
        return [dict(zip(headers, row)) for row in values[1:] if any(v is not None for v in row)], list(
            headers
        )
    finally:
        book.close()


def read_work(directory):
    paths = {name: resolve_input(directory, name) for name in EXPECTED_FILES}
    catalog, cat_headers = workbook_rows(paths[CATALOG])
    audit, audit_headers = workbook_rows(paths["EU_Regulation_Source_Audit.xlsx"])
    with paths[MANIFEST].open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        manifest = list(reader)
        manifest_headers = reader.fieldnames
    for name in ["EU_Regulation_RAG_Schema.md", "EU_Regulation_Research_Report.md"]:
        if not paths[name].read_text(encoding="utf-8-sig").strip():
            raise ValueError("Empty research markdown")
    required = {
        "优先级",
        "主题",
        "法规/规则编号",
        "官方标题（EN）",
        "CELEX",
        "官方 ELI URL",
        "核实级别",
        "下载状态",
    }
    if not required <= set(cat_headers):
        raise ValueError("Work catalog schema changed; explicit mapping needed")
    if not {
        "act_number",
        "priority",
        "celex",
        "language",
        "official_url",
        "original_pdf_url",
        "download_status",
    } <= set(manifest_headers):
        raise ValueError("Work manifest schema changed")
    return {
        "catalog": catalog,
        "manifest": manifest,
        "source_audit": audit,
        "headers": {"catalog": cat_headers, "manifest": manifest_headers, "source_audit": audit_headers},
        "files": [
            {
                "name": name,
                "actual_name": p.name,
                "bytes": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            }
            for name, p in paths.items()
        ],
    }


def normalized_entries(work, include_consolidated=True):
    catalog_by_number = {row["法规/规则编号"]: row for row in work["catalog"]}
    entries = []
    quarantine = []
    for row in work["manifest"]:
        catalog = catalog_by_number.get(row["act_number"])
        if not catalog:
            quarantine.append(
                {
                    "act_number": row["act_number"],
                    "reason": "No exact master catalog match",
                    "source_row": row,
                }
            )
            continue
        try:
            entry = ManifestEntry(
                regulation_number=row["act_number"],
                title=catalog["官方标题（EN）"],
                celex=row["celex"],
                eli=catalog.get("官方 ELI URL") or None,
                official_url=row["official_url"],
                download_url=row["original_pdf_url"],
                language=row["language"],
                version_kind="official",
                format="pdf",
                priority=row["priority"],
                topic=catalog["主题"],
                document_type=row["document_type"],
                research_metadata={
                    "catalog_row": catalog,
                    "manifest_row": row,
                    "status_note": "Research claim preserved, not current verified legal status or downloaded bytes",
                },
            )
            entries.append(entry)
            url = row.get("consolidated_url", "")
            match = re.search(r"/(\d{4}-\d{2}-\d{2})/", url)
            if include_consolidated and url and match:
                version_date = match.group(1)
                entries.append(
                    ManifestEntry(
                        **(
                            entry.model_dump()
                            | {
                                "celex": "0" + entry.celex[1:] + "-" + version_date.replace("-", ""),
                                "version_kind": "consolidated",
                                "version_date": version_date,
                                "download_url": url,
                                "research_metadata": entry.research_metadata
                                | {
                                    "consolidated_identity_derived_from_declared_url_date": True,
                                    "legal_force_note": "Documentary only; URL date is a candidate, not confirmed current applicability",
                                },
                            }
                        )
                    )
                )
        except ValueError as exc:
            quarantine.append({"act_number": row["act_number"], "reason": str(exc)[:400], "source_row": row})
    return entries, quarantine


def import_work(session, directory, snapshot_path):
    work = read_work(directory)
    entries, quarantine = normalized_entries(work)
    for entry in entries:
        register(session, entry)
    snapshot = {
        **work,
        "quarantine": quarantine,
        "imported_at": utcnow().isoformat(),
        "counts": {
            "catalog": len(work["catalog"]),
            "priorities": dict(Counter(r["优先级"] for r in work["catalog"])),
            "manifest": len(work["manifest"]),
            "research_review_levels": dict(Counter(r["核实级别"] for r in work["catalog"])),
            "normalized_document_targets": len(entries),
            "quarantined_manifest_rows": len(quarantine),
        },
    }
    path = Path(snapshot_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return snapshot
