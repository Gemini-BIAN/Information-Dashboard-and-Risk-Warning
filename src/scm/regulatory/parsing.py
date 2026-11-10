import json
import re
from collections import Counter
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from pypdf import PdfReader
from sqlalchemy import delete

from scm.regulatory.models import RegulationChunk
from scm.regulatory.storage import checked_path

BOUNDARY = re.compile(r"^\s*(Article\s+(\d+[a-z]?)|ANNEX\s+([IVXLCDM]+|\d+))\b", re.I)


def tokenize(text):
    return re.findall(r"[a-z]+(?:-[a-z]+)?|\d+", text.lower())


def pages_from_file(path, format):
    if format == "pdf":
        reader = PdfReader(path)
        return [
            (i + 1, page.extract_text() or "", ["PDF_LAYOUT_REQUIRES_REVIEW"])
            for i, page in enumerate(reader.pages)
        ]
    text = path.read_text(encoding="utf-8-sig")
    if format == "html":
        soup = BeautifulSoup(text, "html.parser")
        content = soup.find("article") or soup.find("main") or soup.select_one("#document1")
        if content is None:
            raise ValueError("No legal content container")
        flags = ["TABLE_REQUIRES_REVIEW"] if content.find("table") else []
        for node in content.select("script,style,nav,footer,form"):
            node.decompose()
        return [(None, content.get_text("\n", strip=True), flags)]
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError("XML DTD/entity unsupported")
    root = ElementTree.fromstring(text)
    # Baseline text traversal only; legal XML structural semantics remain unverified.
    return [
        (None, "\n".join(t.strip() for t in root.itertext() if t.strip()), ["XML_STRUCTURE_REQUIRES_REVIEW"])
    ]


def extract_chunks(pages, max_chars=2200):
    units = []
    current = {"type": "preamble", "label": "", "lines": [], "pages": [], "flags": set()}
    for page, text, flags in pages:
        if not text.strip():
            current["flags"].add("EMPTY_PAGE_OCR_REQUIRED")
        for line in text.splitlines():
            match = BOUNDARY.match(line)
            if match:
                if current["lines"]:
                    units.append(current)
                kind = "article" if match.group(2) else "annex"
                current = {
                    "type": kind,
                    "label": match.group(2) or match.group(3),
                    "lines": [],
                    "pages": [],
                    "flags": set(),
                }
                if kind == "annex":
                    current["flags"].add("ANNEX_REQUIRES_REVIEW")
            current["lines"].append(line)
            current["pages"].append(page)
            current["flags"].update(flags)
    if current["lines"]:
        units.append(current)
    chunks = []
    for unit in units:
        text = "\n".join(unit["lines"]).strip()
        if not text:
            continue
        for start in range(0, len(text), max_chars):
            quote = text[start : start + max_chars]
            numbers = [p for p in unit["pages"] if p is not None]
            chunks.append(
                dict(
                    unit_type=unit["type"],
                    unit_label=unit["label"],
                    text=quote,
                    page_start=min(numbers) if numbers else None,
                    page_end=max(numbers) if numbers else None,
                    locator=f"{unit['type']} {unit['label']} unit_text[{start}:{start + len(quote)}]",
                    quality_json=json.dumps(sorted(unit["flags"])),
                    terms_json=json.dumps(Counter(tokenize(quote))),
                )
            )
    return chunks


def parse_document(session, row, root):
    if row.download_status != "downloaded":
        raise ValueError("Only hash-verified downloaded documents can be parsed")
    meta = json.loads(row.metadata_json)
    try:
        path = checked_path(row, root)
        pages = pages_from_file(path, meta["format"])
        chunks = extract_chunks(pages)
        if not chunks:
            raise ValueError("No extractable text; OCR/manual handling required")
        session.execute(delete(RegulationChunk).where(RegulationChunk.document_id == row.id))
        for ordinal, chunk in enumerate(chunks):
            session.add(RegulationChunk(document_id=row.id, ordinal=ordinal, **chunk))
        flags = sorted({flag for c in chunks for flag in json.loads(c["quality_json"])})
        row.parse_status = "needs_review" if flags else "parsed"
        row.quality_json = json.dumps(flags)
        row.error = None
        session.flush()
        return {"chunks": len(chunks), "parse_status": row.parse_status, "flags": flags}
    except Exception as exc:
        row.parse_status = "failed"
        row.error = type(exc).__name__ + ": " + str(exc)[:240]
        # No stale successful chunks may remain searchable after parse failure.
        session.execute(delete(RegulationChunk).where(RegulationChunk.document_id == row.id))
        return {"chunks": 0, "parse_status": "failed", "error": row.error}
