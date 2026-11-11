import json
import re
from collections import Counter
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from pypdf import PdfReader
from sqlalchemy import delete

from scm.regulatory.models import RegulationChunk
from scm.regulatory.storage import checked_path

BOUNDARY = re.compile(r"^\s*(Article\s+(\d+[a-z]?)|ANNEX\s+([IVXLCDM]+|\d+))\s*$", re.I)


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
    """Keep headings/paragraph boundaries and exact extracted offsets, with per-chunk page ranges.

    Strict whole-line headings avoid Article7/Article2 rows in correlation tables.
    Whitespace on the next page must never extend a prior provision's page range.
    """
    units = []
    current = {"type": "preamble", "label": "", "lines": [], "flags": set()}
    annex_section = False
    for page, text, flags in pages:
        if not text.strip():
            current["flags"].add("EMPTY_PAGE_OCR_REQUIRED")
        for line in text.splitlines():
            match = BOUNDARY.fullmatch(line)
            if match and annex_section and match.group(2):
                match = None
            if match:
                if current["lines"]:
                    units.append(current)
                kind = "article" if match.group(2) else "annex"
                annex_section = annex_section or kind == "annex"
                current = {
                    "type": kind,
                    "label": match.group(2) or match.group(3),
                    "lines": [],
                    "flags": set(),
                }
                if kind == "annex":
                    current["flags"].add("ANNEX_REQUIRES_REVIEW")
            current["lines"].append((line, page))
            current["flags"].update(flags)
    if current["lines"]:
        units.append(current)
    chunks = []
    for unit in units:
        lines = unit["lines"]
        while lines and not lines[0][0].strip():
            lines = lines[1:]
        while lines and not lines[-1][0].strip():
            lines = lines[:-1]
        text = "\n".join(line for line, _ in lines)
        if not text.strip():
            continue
        spans = []
        offset = 0
        for line, page in lines:
            if line.strip():
                spans.append((offset, offset + len(line), page))
            offset += len(line) + 1
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            flags = set(unit["flags"])
            if end < len(text):
                # Prefer full paragraphs, then full source lines; never silently cut words.
                preferred = [
                    m.start()
                    for m in re.finditer(r"\n(?=(?:\d+\.|\([a-z0-9]+\))\s)", text[start:end])
                    if m.start() > max_chars // 3
                ]
                if preferred:
                    end = start + preferred[-1]
                else:
                    split = text.rfind("\n", start + max_chars // 3, end)
                    if split > start:
                        end = split
                    else:
                        flags.add("LONG_PARAGRAPH_SPLIT_REQUIRES_REVIEW")
            quote = text[start:end]
            numbers = [page for a, b, page in spans if page is not None and a < end and b > start]
            if unit["type"] == "preamble":
                flags.add("PREAMBLE_OR_UNSTRUCTURED_TEXT")
            chunks.append(
                dict(
                    unit_type=unit["type"],
                    unit_label=unit["label"],
                    text=quote,
                    page_start=min(numbers) if numbers else None,
                    page_end=max(numbers) if numbers else None,
                    locator=f"{unit['type']} {unit['label']} unit_text[{start}:{end}]",
                    quality_json=json.dumps(sorted(flags)),
                    terms_json=json.dumps(Counter(tokenize(quote))),
                )
            )
            start = end
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
