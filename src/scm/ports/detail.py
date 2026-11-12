"""Read-only detail projections over existing evidence, plus scoped business profile audit records."""

import hashlib
import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from scm.database.models import Analysis, Event, PortAlert, PortSignal, RawRevision, Source
from scm.platform.models import Audit, Evidence, Item, PlatformSource
from scm.platform.service import audit
from scm.ports.engine import grounded_ports
from scm.ports.registry import registry
from scm.ports.service import snapshots


class BusinessProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    usage: str = Field(default="", max_length=1000)
    routes: str = Field(default="", max_length=1000)
    transport: str = Field(default="", max_length=1000)
    cargo: str = Field(default="", max_length=1000)
    alternatives: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def ports(self):
        if set(self.alternatives) - {p.id for p in registry().ports}:
            raise ValueError("Unknown alternative port")
        return self


def profile(session, port_id, mode):
    _validate(port_id, mode)
    row = session.scalar(
        select(Audit)
        .where(Audit.source_id == "port-profile-" + port_id, Audit.mode == mode)
        .order_by(Audit.id.desc())
    )
    return (
        BusinessProfile.model_validate(json.loads(row.payload_json)["profile"]) if row else BusinessProfile()
    )


def save_profile(session, port_id, mode, payload, actor, reason):
    _validate(port_id, mode)
    value = BusinessProfile.model_validate(payload)
    if not actor.strip() or not reason.strip() or port_id in value.alternatives:
        raise ValueError("Reviewer/reason required; a port cannot be its own alternative")
    audit(
        session,
        "port-profile-" + port_id,
        mode,
        {
            "kind": "port_business_profile",
            "profile": value.model_dump(),
            "actor": actor.strip(),
            "reason": reason.strip(),
        },
    )
    return value


def _validate(port_id, mode):
    if port_id not in {p.id for p in registry().ports} or mode not in ["live", "demo", "manual"]:
        raise ValueError("Explicit registered port and namespace required")


def detail(session, port_id, mode):
    _validate(port_id, mode)
    snap = snapshots(session, mode)[port_id]
    records = []
    signals = list(session.scalars(select(PortSignal).where(PortSignal.data_mode == mode)))
    # Current assessment is always supplied by the original risk service; history never overrides it.
    current = {e["signal_id"]: e for e in snap["events"]}
    for signal in signals:
        event_id = signal.event_id
        if signal.id not in current:
            continue
        event = session.get(Event, event_id)
        source = session.get(Source, event.source_id)
        candidates = list(
            session.scalars(
                select(RawRevision)
                .join(Event, RawRevision.event_id == Event.id)
                .where(Event.source_id == signal.source_id, Event.data_mode == mode)
                .order_by(RawRevision.id)
            )
        )
        versions = []
        for revision in candidates:
            stored = session.scalar(
                select(Analysis).where(Analysis.revision_id == revision.id).order_by(Analysis.id.desc())
            )
            provenance = json.loads(stored.payload_json).get("port01", {}) if stored else {}
            if provenance.get("notice", {}).get("external_id") == signal.external_id:
                versions.append((revision, stored, provenance))
        for n, (revision, stored, provenance) in enumerate(versions, 1):
            latest = revision.event_id == event_id and revision.content_hash == event.content_hash
            evidence = current[signal.id]
            notice = provenance.get("notice", evidence["notice"])
            stored = session.scalar(
                select(Analysis).where(Analysis.revision_id == revision.id).order_by(Analysis.id.desc())
            )
            records.append(
                {
                    "id": f"raw-{revision.id}",
                    "version": n,
                    "latest": latest,
                    "category": provenance.get("assessment", evidence["assessment"])["kind"],
                    "state": evidence["assessment"]["lifecycle"] if latest else "historical_version",
                    "current": latest
                    and evidence["assessment"]["state"] in ["confirmed_disruption", "confirmed_normal"],
                    "title": revision.title,
                    "body": revision.body,
                    "url": revision.source_url,
                    "published": revision.published_at,
                    "fetched": revision.fetched_at,
                    "effective": notice.get("valid_from"),
                    "until": notice.get("valid_until"),
                    "publisher": source.name,
                    "sha256": revision.content_hash,
                    "body_sha256": hashlib.sha256(revision.body.encode("utf-8")).hexdigest(),
                    "review": event.review_status if latest else "historical_version",
                    "assessment_id": stored.id if stored else None,
                    "mode": mode,
                    "background": False,
                }
            )
    # Platform background/manual records are evidence-only; never added to operational snapshots.
    for item in session.scalars(select(Item).where(Item.mode == mode, Item.module == "ports")):
        versions = list(
            session.scalars(select(Evidence).where(Evidence.item_id == item.id).order_by(Evidence.version))
        )
        for ev in versions:
            raw = json.loads(ev.raw_json)
            if not grounded_ports(raw["title"] + "\n" + raw["body"], [port_id]):
                continue
            src = session.get(PlatformSource, item.source_id)
            records.append(
                {
                    "id": f"platform-{ev.id}",
                    "version": ev.version,
                    "latest": ev.version == item.version,
                    "category": "background",
                    "state": "background",
                    "current": False,
                    "title": raw["title"],
                    "body": raw["body"],
                    "url": raw["url"],
                    "published": raw["published_at"],
                    "fetched": raw["fetched_at"],
                    "effective": None,
                    "until": None,
                    "publisher": json.loads(src.spec_json).get("name", item.source_id),
                    "sha256": ev.sha256,
                    "body_sha256": hashlib.sha256(raw["body"].encode("utf-8")).hexdigest(),
                    "review": item.review_status if ev.version == item.version else "historical_version",
                    "assessment_id": None,
                    "mode": mode,
                    "background": True,
                }
            )
    records.sort(
        key=lambda r: (
            datetime.fromisoformat(r["effective"] or r["published"]).timestamp()
            if r["effective"] or r["published"]
            else float("-inf")
        ),
        reverse=True,
    )
    alerts = [
        a
        for a in session.scalars(select(PortAlert).where(PortAlert.data_mode == mode))
        if port_id in json.loads(a.summary_json)["assessment"]["ports"]
    ]
    return {
        "snapshot": snap,
        "records": records,
        "alerts": alerts,
        "profile": profile(session, port_id, mode),
    }
