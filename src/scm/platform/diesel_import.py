"""Import output of an existing collector. This module makes no network requests."""

import csv
import hashlib
import io
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from scm.platform.contracts import Record
from scm.platform.models import Evidence, Item
from scm.platform.service import audit, ingest, register


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin_source_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    source_url: str
    country: str
    observed_date: date
    fuel_type: str = "diesel"
    value: Decimal = Field(gt=0, allow_inf_nan=False)
    currency: str
    unit: str
    fetched_at: datetime
    method: str = Field(min_length=1, max_length=200)

    @field_validator("fuel_type")
    @classmethod
    def diesel_only(cls, v):
        if v != "diesel":
            raise ValueError("Diesel output only")
        return v


def load(factory, content, filename, actor, reason):
    if not actor.strip() or not reason.strip() or len(content) > 2_000_000:
        raise ValueError("Reviewer, reason and file <=2MB required")
    if filename.lower().endswith(".json"):
        rows = json.loads(content.decode("utf-8-sig"))
    elif filename.lower().endswith(".csv"):
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    else:
        raise ValueError("CSV/JSON only")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
        raise ValueError("1–1000 observations required")
    validated = []
    for raw in rows:
        value = Observation.model_validate(raw)
        amount = value.value
        unit = value.unit
        if unit == "EUR/1000l" and value.currency.upper() == "EUR":
            amount /= 1000
            unit = "EUR/litre"
        body = value.model_dump_json()
        # Origin is the publisher, not the name of the user's scraper.
        key = f"{value.origin_source_id}|{Record.countries(value.country)}|{value.observed_date}|diesel|{value.currency.upper()}|{unit}"
        rec = Record(
            external_id=hashlib.sha256(key.encode()).hexdigest(),
            module="market",
            title=f"柴油导入｜{value.country}｜{value.observed_date}",
            body=body,
            url=value.source_url,
            observed_at=datetime.combine(value.observed_date, datetime.min.time(), tzinfo=timezone.utc),
            fetched_at=value.fetched_at,
            mode="manual",
            verification="MANUAL",
            country=value.country,
            value=amount,
            currency=value.currency,
            unit=unit,
            price_type="observed_price",
            origin_source_id=value.origin_source_id,
            evidence_quote=body,
        )
        validated.append(rec)
    counts = {"inserted": 0, "unchanged": 0, "conflicts": 0}
    with factory.begin() as session:
        register(
            session,
            [
                dict(
                    id="diesel-output-import",
                    name="Existing diesel tool output (Manual)",
                    adapter="manual",
                    url="https://example.invalid/import",
                    automatic_access_allowed=False,
                )
            ],
        )
        for rec in validated:
            duplicate = None
            for item in session.scalars(select(Item).where(Item.module == "market", Item.mode != "demo")):
                ev = session.scalar(
                    select(Evidence).where(Evidence.item_id == item.id, Evidence.version == item.version)
                )
                old = json.loads(ev.raw_json)
                origin = old.get("origin_source_id") or item.source_id
                if (
                    origin,
                    old["country"],
                    datetime.fromisoformat(old["observed_at"]) if old.get("observed_at") else None,
                    old.get("currency"),
                    old.get("unit"),
                ) == (rec.origin_source_id, rec.country, rec.observed_at, rec.currency, rec.unit):
                    duplicate = old
                    break
            if duplicate:
                equal = duplicate.get("value") is not None and Decimal(duplicate["value"]) == rec.value
                counts["unchanged" if equal else "conflicts"] += 1
                if not equal:
                    audit(
                        session,
                        "diesel-conflict",
                        "manual",
                        {
                            "actor": actor,
                            "reason": reason,
                            "incoming": rec.model_dump(mode="json"),
                            "existing": duplicate,
                            "action": "retained both claims in audit; official observation not overwritten",
                        },
                    )
            else:
                outcome, _ = ingest(session, "diesel-output-import", rec)
                counts[outcome] += 1
        audit(session, "diesel-output-import", "manual", {"actor": actor, "reason": reason, "writes": counts})
    return counts


def series(session, mode, origin, country, currency, unit):
    from scm.platform.service import rows

    values = [
        r["raw"]
        for r in rows(session, mode, "market")
        if (r["raw"].get("origin_source_id") or r["source_id"]) == origin
        and r["raw"]["country"] == country
        and r["raw"].get("currency") == currency
        and r["raw"].get("unit") == unit
        and r["raw"].get("observed_at")
        and r["raw"].get("value") is not None
    ]
    values.sort(key=lambda r: r["observed_at"])
    result = []
    for raw in values:
        at = datetime.fromisoformat(raw["observed_at"])
        prior = next(
            (p for p in values if datetime.fromisoformat(p["observed_at"]) == at - timedelta(days=7)), None
        )
        change = (
            (Decimal(raw["value"]) / Decimal(prior["value"]) - 1) * 100
            if prior and Decimal(prior["value"]) > 0
            else None
        )
        result.append(
            {
                "observed_at": raw["observed_at"],
                "value": raw["value"],
                "weekly_change_pct": str(change) if change is not None else None,
                "quality": "missing_comparable_week"
                if change is None
                else "review_large_change"
                if abs(change) > 20
                else "comparable_week",
            }
        )
    return result
