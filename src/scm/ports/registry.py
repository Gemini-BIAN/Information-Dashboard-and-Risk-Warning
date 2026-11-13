import json

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scm.settings import ROOT, TIMEZONE


class Port(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    business_label: str
    name_zh: str
    country: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    aliases: list[str]
    watch_enabled: bool
    unlocode: str | None = None
    coordinate_precision: str
    scope_confirmed: bool = True
    scope_note: str
    source_ids: list[str]


class Registry(BaseModel):
    schema_version: str
    current_evidence_hours: int = Field(ge=1, le=168)
    ports: list[Port]

    @model_validator(mode="after")
    def unique_ids(self):
        if len({p.id for p in self.ports}) != len(self.ports):
            raise ValueError("Duplicate port id")
        return self


def registry():
    return Registry.model_validate_json((ROOT / "config/ports.json").read_text(encoding="utf-8"))


def source_specs():
    return json.loads((ROOT / "config/port_sources.json").read_text(encoding="utf-8"))


def initial_snapshot(port, now):
    sources = [s for s in source_specs() if s["id"] in port.source_ids]
    return {
        "port": port.model_dump(),
        "as_of": now.astimezone(TIMEZONE).isoformat(),
        "state": "unknown",
        "severity": "unknown",
        "relevance": "unknown",
        "coverage": sources,
        "last_check": None,
        "last_success": None,
        "events": [],
        "note": "没有合格当前运营证据；无预警不等于正常。",
        "metrics": "船舶动态 / AIS / ETA / 拥堵与等待时间：预留，未接入。",
    }
