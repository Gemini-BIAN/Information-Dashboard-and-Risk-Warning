"""Official EC workbook adapter: observation dates and cells, never filename dates."""

import io
import json
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from openpyxl import load_workbook

from scm.platform.contracts import Record
from scm.settings import utcnow

COUNTRIES = {"Germany": "DE", "France": "FR", "Belgium": "BE", "Netherlands": "NL"}


def parse_workbook(content, url, verification):
    if not content.startswith(b"PK"):
        raise ValueError("Not XLSX bytes")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        if sum(f.file_size for f in archive.infolist()) > 20_000_000:
            raise ValueError("Workbook expansion limit")
    w = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
    try:
        sheet = w["Sheet1"]
        if (
            sheet["A1"].value != "in EUR"
            or sheet["C2"].value != "1000 l"
            or "gas oil" not in str(sheet["C1"].value).lower()
        ):
            raise ValueError("Unexpected workbook currency/unit/product schema")
        observed = sheet["A2"].value
        if not isinstance(observed, datetime) or observed.tzinfo is not None:
            raise ValueError("No unambiguous workbook observation day")
        records = []
        for row in sheet.iter_rows(min_row=3):
            if row[0].value not in COUNTRIES:
                continue
            if row[2].data_type == "f" or not isinstance(row[2].value, (int, float)):
                raise ValueError("Price cell must be numeric, not formula")
            number = Decimal(str(row[2].value))
            if not number.is_finite() or number < 0:
                raise ValueError("Invalid price")
            cells = {
                "Sheet1!A1": sheet["A1"].value,
                "Sheet1!A2": observed.date().isoformat(),
                "Sheet1!C1": sheet["C1"].value,
                "Sheet1!C2": sheet["C2"].value,
                f"Sheet1!A{row[0].row}": row[0].value,
                f"Sheet1!C{row[2].row}": str(number),
            }
            body = json.dumps(cells, ensure_ascii=False, sort_keys=True)
            demo = verification != "LIVE_HTTP"
            records.append(
                Record(
                    external_id=("DEMO-" if demo else "")
                    + f"ec-diesel-{COUNTRIES[row[0].value]}-{observed.date()}",
                    module="market",
                    title=("DEMO · " if demo else "") + f"柴油价格观测｜{row[0].value}｜{observed.date()}",
                    body=body,
                    url=url,
                    published_at=None,
                    observed_at=observed.replace(tzinfo=timezone.utc),
                    fetched_at=utcnow(),
                    mode="demo" if demo else "live",
                    verification="DEMO" if demo else "LIVE_HTTP",
                    country=COUNTRIES[row[0].value],
                    value=number / Decimal(1000),
                    currency="EUR",
                    unit="EUR/litre",
                    price_type="observed_price",
                    evidence_quote=body,
                )
            )
        if len(records) != len(COUNTRIES):
            raise ValueError("Missing expected country observation rows")
        return records
    finally:
        w.close()


def fetch(spec, fetcher):
    page = fetcher.get(spec["url"])
    soup = BeautifulSoup(page.text, "html.parser")
    candidates = [
        a["href"]
        for a in soup.select("a[href]")
        if "weekly%20prices%20with%20taxes" in a["href"].lower() and ".xlsx" in a["href"].lower()
    ]
    if len(candidates) != 1:
        raise ValueError("Ambiguous/missing official with-tax workbook link")
    url = urljoin(spec["url"], candidates[0])
    from urllib.parse import urlsplit

    if urlsplit(url).hostname != urlsplit(spec["url"]).hostname:
        raise ValueError("Unapproved workbook host")
    response = fetcher.get(url)
    if "spreadsheetml.sheet" not in response.headers.get("content-type", ""):
        raise ValueError("Expected XLSX MIME")
    return parse_workbook(response.content, url, fetcher.verification_type), {
        "http_status": response.status_code,
        "date_basis": "Workbook A2, day precision; UTC midnight convention; publication unknown",
        "normalization": "EUR/1000 l divided by1000 to EUR/litre; no FX or contract-cost inference",
    }
