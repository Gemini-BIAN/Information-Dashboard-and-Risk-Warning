"""Validated input contracts; dates, provenance and measurements are explicit."""

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Mode = Literal["live", "demo", "manual"]
Module = Literal["ports", "capacity", "market"]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_id: str = Field(min_length=1, max_length=200)
    module: Module
    title: str = Field(min_length=1, max_length=1000)
    body: str = Field(min_length=1, max_length=200000)
    url: str
    published_at: datetime | None = None
    fetched_at: datetime
    mode: Mode
    verification: Literal["LIVE_HTTP", "DEMO", "MANUAL"]
    data_status: Literal["verified", "candidate", "unavailable", "failed"] = "candidate"
    country: str = "unknown"
    company: str = "unknown"
    project_id: str | None = None
    factory: str | None = None
    project_status: Literal[
        "announced", "under_construction", "commissioning", "operating", "delayed", "cancelled", "unknown"
    ] = "unknown"
    capacity: Decimal | None = Field(default=None, ge=0)
    capacity_unit: Literal["GWh/year", "MWh/year", "tonnes/year"] | None = None
    investment: Decimal | None = Field(default=None, ge=0)
    planned_start: str | None = None
    value: Decimal | None = Field(default=None, ge=0)
    currency: str | None = None
    unit: Literal["USD/FEU", "EUR/FEU", "EUR/litre", "USD/tonne", "index_points", "EUR/container"] | None = (
        None
    )
    price_type: Literal["announcement", "observed_price", "index", "manual_input", "model_estimate"] = (
        "announcement"
    )
    route: str | None = None
    evidence_quote: str | None = None

    @field_validator("published_at", "fetched_at")
    @classmethod
    def timezone_required(cls, v):
        if v is not None and v.tzinfo is None:
            raise ValueError("Timezone required; date-only input must specify an offset")
        return v.astimezone(timezone.utc) if v else v

    @field_validator("url")
    @classmethod
    def public_url(cls, v):
        p = urlsplit(v)
        if p.scheme != "https" or not p.hostname or p.username or p.password or p.port not in [443, None]:
            raise ValueError("An HTTPS evidence URL without credentials is required")
        return v.split("#")[0]

    @field_validator("country")
    @classmethod
    def countries(cls, v):
        aliases = {
            "germany": "DE",
            "德国": "DE",
            "france": "FR",
            "法国": "FR",
            "china": "CN",
            "中国": "CN",
            "netherlands": "NL",
            "belgium": "BE",
            "uk": "GB",
        }
        v = aliases.get(v.strip().casefold(), v.strip())
        if v == "unknown":
            return v
        v = v.upper()
        if not re.fullmatch(r"[A-Z]{2}", v):
            raise ValueError("Use ISO alpha-2 country code or configured alias")
        return v

    @field_validator("currency")
    @classmethod
    def currencies(cls, v):
        if v is None:
            return v
        v = v.upper().strip()
        if v not in ["USD", "EUR", "GBP", "CNY", "JPY"]:
            raise ValueError("Unsupported currency; no implicit FX conversion")
        return v

    @field_validator("planned_start")
    @classmethod
    def planned_date(cls, v):
        if v is not None:
            from datetime import date

            date.fromisoformat(v)
        return v

    @model_validator(mode="after")
    def provenance(self):
        if self.verification != {"live": "LIVE_HTTP", "demo": "DEMO", "manual": "MANUAL"}[self.mode]:
            raise ValueError("Mode/provenance mismatch; injected test clients cannot enter Live")
        if self.mode == "demo" and not (self.external_id.startswith("DEMO-") and "DEMO" in self.title):
            raise ValueError("Synthetic records require explicit DEMO id/title")
        if self.mode != "demo" and (self.external_id.startswith("DEMO-") or "example.invalid" in self.url):
            raise ValueError("Demo identifiers/URLs cannot enter Live or Manual")
        if self.mode == "live" and self.data_status == "verified":
            raise ValueError("HTTP collection verifies provenance, not facts; retain candidate")
        structured = (
            any(
                v is not None
                for v in [self.capacity, self.investment, self.value, self.project_id, self.planned_start]
            )
            or self.project_status != "unknown"
        )
        if structured and (not self.evidence_quote or self.evidence_quote not in self.body):
            raise ValueError("Structured claims require a verbatim supporting evidence quote")
        if self.capacity is not None and not self.capacity_unit:
            raise ValueError("Capacity needs an explicit unit")
        if self.investment is not None and not self.currency:
            raise ValueError("Investment needs a currency")
        if self.value is not None and not self.unit:
            raise ValueError("Price/index requires unit")
        if self.value is not None and self.unit[:3] in ["USD", "EUR"] and not self.currency:
            raise ValueError("Monetary observations require currency")
        if self.value is not None and self.price_type == "announcement":
            raise ValueError("Announcements cannot masquerade as measured prices")
        if self.unit and self.currency and self.unit[:3] in ["EUR", "USD"] and self.unit[:3] != self.currency:
            raise ValueError("Currency and price unit disagree")
        for v in [self.capacity, self.investment, self.value]:
            if v is not None and not v.is_finite():
                raise ValueError("Finite measurements required")
        return self
