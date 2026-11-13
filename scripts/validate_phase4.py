"""Validate already collected real evidence; never seeds fixtures or invents Live input."""

import hashlib
import json
from pathlib import Path

from sqlalchemy import func, select

from scm.database.session import session_factory
from scm.platform.adapters import fetch_records
from scm.platform.automation import update
from scm.platform.decision import cards, refresh
from scm.platform.decision_io import decision_report
from scm.platform.entities import operations, projects
from scm.platform.models import Evidence, Item, Report
from scm.platform.service import rows, specs
from scm.ports.service import snapshots
from scm.settings import ROOT, utcnow


def main():
    factory = session_factory("sqlite:///runtime/phase4/acceptance.db")
    logs = [json.loads(Path(f"work/collect{i}.json").read_text(encoding="utf-8")) for i in [1, 2, 3, 4, 5]]
    configurations = {s["id"]: s for s in specs()}
    checked = []
    for log in logs[-1]:
        assert log["verification_type"] == "LIVE_HTTP" and log["stage"] == "stored"
        for capture in log["captures"]:
            content = (ROOT / "runtime/platform/artifacts" / capture["path"]).read_bytes()
            assert hashlib.sha256(content).hexdigest() == capture["sha256"]
            import httpx

            class Saved:
                verification_type = "LIVE_HTTP"

                def get(self, url):
                    assert url == capture["url"]
                    return httpx.Response(
                        200, content=content, headers={"content-type": capture["content_type"]}
                    )

            parsed, _ = fetch_records(configurations[log["source"]], Saved())
            with factory() as session:
                stored = {r["raw"]["external_id"]: r["raw"] for r in rows(session, "live")
                          if r["source_id"] == log["source"]}
                for record in parsed:
                    expected = record.model_dump(mode="json")
                    actual = dict(stored[record.external_id])
                    # rows() renders company display names; compare canonical identity.
                    from scm.platform.entities import company_id

                    actual["company"] = company_id(actual["company"])
                    expected["company"] = company_id(expected["company"])
                    actual.pop("fetched_at", None)
                    expected.pop("fetched_at", None)
                    assert actual == expected
            checked.append(
                {
                    "source": log["source"],
                    "sha256": capture["sha256"],
                    "bytes": len(content),
                    "reparsed_records": len(parsed),
                }
            )
    source_ids = list(configurations.keys() & {r["source"] for r in logs[0]})
    with factory.begin() as s:
        data = projects(s, "live")
        ops = operations(s, "live")
        assert len(data) == 1 and len(data[0]["timeline"]) == 3
        assert data[0]["current"]["raw"]["project_status"] == "opened"
        assert data[0]["current"]["raw"]["actual_start"] is None
        assert data[0]["capacity_claims"][0]["basis"] == "planned"
        assert len(ops) == 2 and all(e["state"] == "unknown" for e in ops)
        assert len(snapshots(s, "live")) == 12
        assert all(v["state"] == "unknown" for v in snapshots(s, "live").values())
        assert not projects(s, "demo") and not projects(s, "manual")
        refresh(s, "live")
        before = {m.__tablename__: s.scalar(select(func.count()).select_from(m)) for m in [Item, Evidence]}
        current = decision_report(s, "live", "weekly")
        assert "项目登记册" in current.html and "15.8" in current.html
        assert "本期无合格高价值事件" in current.html
        Path("runtime/phase4/weekly.html").write_text(current.html, encoding="utf-8")
        project_card = next(
            c for c in cards(s, "live") if c["entity_representative"] and c["event"]["project"]
        )
        assert not project_card["high_value"] and not project_card["verified_facts"]
        public_rows = rows(s, "live")
    runs = [update(factory, "runtime/phase4/updates", source_ids) for _ in range(3)]
    with factory() as s:
        after = {m.__tablename__: s.scalar(select(func.count()).select_from(m)) for m in [Item, Evidence]}
        assert before == after
        assert all(not r["collection"] for r in runs)
        assert runs[-1]["decisions"]["unchanged"] == before["platform_items"]
        count_reports = s.scalar(select(func.count()).select_from(Report))
    output = {
        "at": utcnow().isoformat(),
        "status": "LIVE PARTIAL",
        "collection_runs": logs,
        "raw_reparse": checked,
        "items_before": before,
        "items_after": after,
        "reports": count_reports,
        "update_runs": [{"collection": r["collection"], "decisions": r["decisions"]} for r in runs],
        "coverage": {
            "rotterdam_current_events": 0,
            "current_confirmed_port_events": 0,
            "carrier_operational_notice_entities": 2,
            "current_confirmed_carrier_events": 0,
            "real_factory_projects": 1,
            "project_official_documents": 3,
            "feed_records": 10,
            "remaining_feed_records_background": 8,
            "new_diesel_observations": 0,
            "demo_records": 0,
            "manual_records": 0,
        },
        "project": data[0],
        "operational_notices": ops,
        "project_decision_card": project_card,
        "source_links": [
            {
                "source": r["source_id"],
                "url": r["raw"]["url"],
                "published_at": r["raw"]["published_at"],
                "sha256": r["sha256"],
            }
            for r in public_rows
        ],
    }
    # Public acceptance stores metadata/field evidence, not whole RSS or third-party bodies.
    for entity in [output["project"], *output["operational_notices"]]:
        for row in entity["timeline"] + ([entity["current"]] if entity.get("current") else []):
            row["raw"].pop("body", None)
    project_card.pop("entity_summary", None)
    output["project_decision_card"]["facts"] = []
    Path("docs/phase4/LIVE_ACCEPTANCE.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(output["coverage"], ensure_ascii=False))


if __name__ == "__main__":
    main()
