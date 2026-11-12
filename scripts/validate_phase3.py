"""Actual approved HTTP→artifact→price event→unknown impact→card→report acceptance."""

import hashlib
import io
import json
from decimal import Decimal

from openpyxl import load_workbook
from sqlalchemy import select

from scm.database.session import session_factory
from scm.platform.adapters import collect
from scm.platform.decision import cards, refresh
from scm.platform.decision_io import decision_report, source_health
from scm.platform.models import Audit, Evidence
from scm.platform.service import specs
from scm.settings import ROOT, utcnow


def main():
    factory = session_factory("sqlite:///runtime/platform/platform.db")
    selected = [s for s in specs() if s["id"] in ["hamburg", "ec-batteries", "ec-weekly-fuel"]]
    result = {
        "verified_at": utcnow().isoformat(),
        "verification_type": "ACTUAL_LIVE_HTTP_AND_SAVED_BYTES",
        "source_collection": collect(factory, selected),
        "checks": [],
    }
    with factory.begin() as session:
        refresh(session, "live")
        fuel = [c for c in cards(session, "live") if c["source_id"] == "ec-weekly-fuel"]
        assert len(fuel) == 4 and all(c["high_value"] for c in fuel)
        log = session.scalar(
            select(Audit)
            .where(Audit.source_id == "ec-weekly-fuel", Audit.mode == "live")
            .order_by(Audit.id.desc())
        )
        payload = json.loads(log.payload_json)
        assert payload["writes"] == {"unchanged": 4}, payload
        capture = next(c for c in payload["captures"] if "spreadsheetml.sheet" in c["content_type"])
        path = ROOT / "runtime/platform/artifacts" / capture["path"]
        content = path.read_bytes()
        assert hashlib.sha256(content).hexdigest() == capture["sha256"] and len(content) == capture["bytes"]
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        sheet = workbook["Sheet1"]
        actual = {
            r[0].value: r[2].value
            for r in sheet.iter_rows(min_row=3)
            if r[0].value in ["Germany", "France", "Belgium", "Netherlands"]
        }
        for card in fuel:
            ev = session.get(Evidence, card["evidence_id"])
            raw = json.loads(ev.raw_json)
            body = json.loads(raw["body"])
            country = next(
                v for k, v in body.items() if k.startswith("Sheet1!A") and k not in ["Sheet1!A1", "Sheet1!A2"]
            )
            assert Decimal(raw["value"]) == Decimal(str(actual[country])) / Decimal(1000)
            assert raw["published_at"] is None and raw["observed_at"].startswith(
                sheet["A2"].value.date().isoformat()
            )
            assert (
                card["impact_level"] == "unknown" and not card["user_context"] and not card["verified_facts"]
            )
            assert all(f["quote"] in raw["body"] for f in card["facts"])
            result["checks"].append(
                {
                    "country": country,
                    "event_id": card["item_id"],
                    "evidence_id": ev.id,
                    "sha256": ev.sha256,
                    "raw_eur_per_1000l": str(actual[country]),
                    "normalized_eur_per_litre": raw["value"],
                    "observed_at": raw["observed_at"],
                    "published_at": None,
                    "card_id": card["card_id"],
                    "impact": "unknown",
                    "quotes_match_saved_cells": True,
                    "processing_state": card["handling_state"],
                }
            )
        workbook.close()
        report = decision_report(session, "live", "weekly")
        assert all(c["title"] in report.html for c in fuel)
        assert "无人工核实事实" in report.html and "DEMO" not in report.html
        output = ROOT / "runtime/phase3/live-decision-weekly.html"
        output.write_text(report.html, encoding="utf-8")
        assert "本期无合格" in decision_report(session, "live", "daily").html
        result.update(
            workbook={
                "url": capture["url"],
                "sha256": capture["sha256"],
                "bytes": capture["bytes"],
                "path": str(path.relative_to(ROOT)),
            },
            health=source_health(session),
            module_counts={
                "ports_current_operational_events": 0,
                "capacity_projects": 0,
                "market_current_price_observations": 4,
            },
            real_records_by_source={
                s["id"]: sum(1 for c in cards(session, "live") if c["source_id"] == s["id"]) for s in selected
            },
            report={
                "weekly_id": report.id,
                "path": str(output.relative_to(ROOT)),
                "daily": "empty by actual date, no padding",
            },
            status="PASS: real official price data closed loop; business impact unknown, no human business verification",
        )
    (ROOT / "docs/phase3/LIVE_ACCEPTANCE.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "market_observations": 4,
                "workbook_sha256": result["workbook"]["sha256"],
                "weekly_report": result["report"]["path"],
            }
        )
    )


if __name__ == "__main__":
    main()
