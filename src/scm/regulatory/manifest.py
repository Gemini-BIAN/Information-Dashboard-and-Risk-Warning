"""Normalized import contract; Work mapping is explicit in regulatory.work."""

import csv
import hashlib
import io
from datetime import date, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

EXPECTED_FILES = (
    "EU_Regulation_Master_Catalog.xlsx",
    "EU_Regulation_Source_Audit.xlsx",
    "EU_Regulation_RAG_Schema.md",
    "EU_Regulation_Research_Report.md",
    "EU_Regulation_Download_Manifest.csv",
)
OFFICIAL_HOSTS = {"eur-lex.europa.eu", "publications.europa.eu", "op.europa.eu", "data.europa.eu"}


def official_url(url):
    p = urlsplit(str(url))
    if (
        p.scheme != "https"
        or p.hostname not in OFFICIAL_HOSTS
        or p.username
        or p.password
        or p.port not in [None, 443]
    ):
        raise ValueError("Only public official EUR-Lex/Cellar/ELI HTTPS URLs are allowed")
    if any(
        k.lower() in {"token", "access_token", "api_key", "password", "secret"} for k in parse_qs(p.query)
    ):
        raise ValueError("Do not store credentials in manifest URLs")
    return str(url)


class ManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    regulation_number: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=500)
    celex: str = Field(pattern=r"^[03]\d{4}[A-Z]\d{4}(?:-\d{8})?$")
    eli: str | None = None
    official_url: str
    download_url: str
    language: str = Field(pattern=r"^[A-Z]{2}$")
    version_kind: Literal["official", "consolidated"]
    version_date: date | None = None
    format: Literal["pdf", "html", "xml"]
    priority: Literal["P0", "P1", "P2"]
    topic: str = ""
    publication_date: date | None = None
    document_type: str = ""
    research_metadata: dict = Field(default_factory=dict)
    source_evidence: dict = Field(default_factory=dict)
    legal_status: Literal["unknown"] = "unknown"
    verification_status: Literal["pending"] = "pending"

    @model_validator(mode="after")
    def provenance(self):
        for url in [self.official_url, self.download_url] + ([self.eli] if self.eli else []):
            official_url(url)
        if self.version_kind == "consolidated" and self.version_date is None:
            raise ValueError("Consolidated text requires explicit version_date; never infer latest")
        if self.version_kind == "official" and not self.celex.startswith("3"):
            raise ValueError("Official act must not use consolidated CELEX identity")
        if self.version_kind == "consolidated" and not self.celex.startswith("0"):
            raise ValueError("Consolidated text requires its own consolidated CELEX identity")
        query = parse_qs(urlsplit(self.download_url).query)
        uri = query.get("uri", [""])[0]
        if uri.startswith("CELEX:") and uri[6:] != self.celex:
            raise ValueError("URL CELEX does not match manifest")
        if self.celex.startswith("0") and "-" in self.celex and self.version_date:
            if self.celex.rsplit("-", 1)[1] != self.version_date.strftime("%Y%m%d"):
                raise ValueError("Consolidated CELEX date conflicts with version_date")
        return self

    def identity(self):
        data = "|".join(
            [self.celex, self.language, self.version_kind, str(self.version_date or "unknown"), self.format]
        )
        return hashlib.sha256(data.encode()).hexdigest()


def load_manifest(path):
    """All-or-nothing validation; no guessing of untranslated Work column names."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Manifest missing: {path.name}; no catalog fabricated")
    if path.suffix.lower() == ".csv":
        reader = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig")))
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or any(not h for h in headers):
            raise ValueError("Duplicate/empty manifest headers")
        rows = list(reader)
    elif path.suffix.lower() == ".xlsx":
        from openpyxl import load_workbook

        book = load_workbook(path, read_only=True, data_only=True)
        try:
            data = book.active.iter_rows(values_only=True)
            headers = next(data, ())
            if (
                not headers
                or len(headers) != len(set(headers))
                or any(not isinstance(h, str) or not h.strip() for h in headers)
            ):
                raise ValueError("Explicit nonempty normalized headers required")
            rows = [dict(zip(headers, row)) for row in data if any(v is not None for v in row)]
        finally:
            book.close()
    else:
        raise ValueError("Only normalized CSV/XLSX manifests supported")
    entries = []
    for row in rows:
        clean = {k: v for k, v in row.items() if v not in [None, ""]}
        if isinstance(clean.get("version_date"), datetime):
            clean["version_date"] = clean["version_date"].date()
        entries.append(ManifestEntry.model_validate(clean))
    if not entries:
        raise ValueError("Empty manifest: no download targets available")
    ids = [e.identity() for e in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate document/version/format identity in manifest")
    return entries


def input_status(directory):
    directory = Path(directory)
    return [
        {
            "name": name,
            "present": (directory / name).is_file()
            or (
                name == "EU_Regulation_Download_Manifest.csv"
                and (directory / "EU_Regulation_Download_Manifest(1).csv").is_file()
            ),
        }
        for name in EXPECTED_FILES
    ]
