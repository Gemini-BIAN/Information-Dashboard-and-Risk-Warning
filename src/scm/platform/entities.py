"""Evidence projections, rebuilt from immutable revisions; no guessed entity matching."""

import json
from datetime import datetime, timedelta

from sqlalchemy import select

from scm.platform.models import Evidence, Item
from scm.settings import ROOT, utcnow


def histories(session, mode, module):
    if mode not in ["live", "demo", "manual"]:
        raise ValueError("Explicit namespace required")
    result = []
    for item in session.scalars(select(Item).where(Item.mode == mode, Item.module == module)):
        for ev in session.scalars(select(Evidence).where(Evidence.item_id == item.id)):
            result.append(
                {
                    "item_id": item.id,
                    "evidence_id": ev.id,
                    "version": ev.version,
                    "review_status": item.review_status,
                    "latest": ev.version == item.version,
                    "raw": json.loads(ev.raw_json),
                    "sha256": ev.sha256,
                }
            )
    return result


def operations(session, mode, now=None):
    """Explicit event IDs are reviewer/adapter supplied, never inferred from similar headlines."""
    now = now or utcnow()
    grouped = {}
    for row in histories(session, mode, "ports"):
        raw = row["raw"]
        if raw.get("operational_event_id"):
            # A shared ID may connect multiple publishers, but scope must agree.
            key = (raw["operational_event_id"], raw["event_scope"])
            grouped.setdefault(key, []).append(row)
    result = []
    for (identity, scope), timeline in grouped.items():
        timeline.sort(key=lambda r: (r["raw"]["status_at"], r["evidence_id"]))
        candidates = [
            r
            for r in timeline
            if r["latest"]
            and r["review_status"] != "rejected"
            and datetime.fromisoformat(r["raw"]["status_at"]) <= now
        ]
        current = candidates[-1] if candidates else None
        state = current["raw"]["operational_status"] if current else "unknown"
        conflict = False
        if current:
            raw = current["raw"]
            at = raw["status_at"]
            conflict = (
                len({r["raw"]["operational_status"] for r in candidates if r["raw"]["status_at"] == at}) > 1
            )
            if conflict:
                state = "unknown"
            elif raw.get("expires_at") and datetime.fromisoformat(raw["expires_at"]) <= now:
                state = "expired"
            elif raw.get("effective_at") and datetime.fromisoformat(raw["effective_at"]) > now:
                state = "scheduled"
            elif state == "active" and now - datetime.fromisoformat(at) > timedelta(hours=24):
                state = "unknown"  # Until further notice is not proof of continuing disruption.
        result.append(
            {
                "event_id": identity,
                "scope": scope,
                "state": state,
                "conflict": conflict,
                "current": current,
                "timeline": timeline,
                "evidence_ids": [r["evidence_id"] for r in candidates],
                "note": "单一事件；解除不等于全港正常；超过24小时持续状态需复核",
            }
        )
    return result


def company_id(value):
    catalog = json.loads((ROOT / "config/platform_companies.json").read_text(encoding="utf-8"))
    for company in catalog["companies"]:
        if value.casefold() in {v.casefold() for v in [company["id"], company["name"], *company["aliases"]]}:
            return company["id"]
    return value


def projects(session, mode):
    grouped = {}
    for row in histories(session, mode, "capacity"):
        raw = row["raw"]
        if raw.get("project_id") and raw.get("factory") and raw["company"] != "unknown":
            key = (company_id(raw["company"]), raw["project_id"])
            grouped.setdefault(key, []).append(row)
    result = []
    for (company, project), timeline in grouped.items():
        timeline.sort(key=lambda r: (r["raw"]["published_at"] or "", r["evidence_id"]))
        claims = [r for r in timeline if r["latest"] and r["review_status"] != "rejected"]
        conflicts = []
        for field in ["factory", "country", "location", "product"]:
            if len({r["raw"].get(field) for r in claims if r["raw"].get(field)}) > 1:
                conflicts.append(field)
        if claims:
            latest_date = claims[-1]["raw"]["published_at"]
            if (
                len({r["raw"]["project_status"] for r in claims if r["raw"]["published_at"] == latest_date})
                > 1
            ):
                conflicts.append("project_status")
        # Distinct dated capacity claims remain separate; never sum GWh and tonnes/year.
        capacities = [
            {
                "value": r["raw"]["capacity"],
                "unit": r["raw"]["capacity_unit"],
                "basis": r["raw"].get("capacity_basis", "unknown"),
                "published_at": r["raw"]["published_at"],
                "evidence_id": r["evidence_id"],
            }
            for r in claims
            if r["raw"].get("capacity") is not None
        ]
        for a in capacities:
            if any(
                b["published_at"] == a["published_at"]
                and b["basis"] == a["basis"]
                and (b["value"], b["unit"]) != (a["value"], a["unit"])
                for b in capacities
            ):
                conflicts.append("capacity")
        if claims:
            result.append(
                {
                    "company_id": company,
                    "project_id": project,
                    "factory_id": claims[-1]["raw"]["factory"],
                    "current": claims[-1],
                    "timeline": timeline,
                    "capacity_claims": capacities,
                    "conflicts": sorted(set(conflicts)),
                    "verified_status": "pending_human_review",
                    "note": "最新公告所述阶段，不证明当前实况；产能为来源口径，非实际产量",
                }
            )
    return result
