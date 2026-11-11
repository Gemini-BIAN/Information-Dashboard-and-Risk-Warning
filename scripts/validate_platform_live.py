"""Actual guarded HTTP acceptance; no mock/fixture seeding. Requires reviewed sources."""

import hashlib
import json
from collections import Counter
from datetime import datetime

from bs4 import BeautifulSoup
from sqlalchemy import select

from scm.collectors.http import SafeFetcher
from scm.collectors.parsers import parse_article
from scm.database.session import session_factory
from scm.platform.adapters import collect, permission_gate
from scm.platform.models import Evidence, PlatformSource
from scm.platform.service import generate_report, rows, specs
from scm.ports.service import snapshots
from scm.settings import ROOT, utcnow


def main():
    factory = session_factory("sqlite:///runtime/platform/platform.db")
    selected = [s for s in specs() if s["id"] in ["hamburg", "ec-batteries"]]
    result = {
        "verified_at": utcnow().isoformat(),
        "verification_type": "LIVE_HTTP",
        "rights": [],
        "source_checks": [],
        "records": [],
    }
    fetcher = SafeFetcher(retries=0)
    try:
        for spec in selected:
            permission_gate(spec, utcnow())
            response = fetcher.get(spec["reuse_policy"]["notice_url"])
            body = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
            probes = ["stored", "shared", "CC BY", "Creative Commons", "reuse", "re-use"]
            excerpts = [
                body[max(0, body.lower().find(p.lower()) - 150) : body.lower().find(p.lower()) + 900]
                for p in probes
                if p.lower() in body.lower()
            ]
            assert excerpts, "Permission review changed; stop and review actual terms"
            result["rights"].append(
                {
                    "source": spec["id"],
                    "url": spec["reuse_policy"]["notice_url"],
                    "http_status": response.status_code,
                    "sha256": hashlib.sha256(response.content).hexdigest(),
                    "excerpts": excerpts,
                    "checked_at": utcnow().isoformat(),
                }
            )
        rerun = collect(factory, selected, fetcher)
        assert sum(r["writes"].get("inserted", 0) for r in rerun) == 0, rerun
        assert sum(r["writes"].get("unchanged", 0) for r in rerun) == 4, rerun
        result["repeat_collection"] = rerun
        with factory.begin() as session:
            real = rows(session, "live")
            assert len(real) == 4
            for r in real:
                raw = r["raw"]
                a = r["analysis"]
                ev = session.get(Evidence, r["evidence_id"])
                stored = json.loads(ev.raw_json)
                fingerprint = hashlib.sha256(
                    json.dumps(
                        {k: v for k, v in stored.items() if k != "fetched_at"},
                        sort_keys=True,
                        ensure_ascii=False,
                    ).encode()
                ).hexdigest()
                assert fingerprint == r["sha256"]
                assert (
                    raw["verification"] == "LIVE_HTTP"
                    and raw["mode"] == "live"
                    and raw["data_status"] == "candidate"
                )
                assert all(f["quote"] in raw["body"] for f in a["facts"])
                result["records"].append(
                    {
                        "id": r["id"],
                        "module": raw["module"],
                        "title": raw["title"],
                        "url": raw["url"],
                        "published_at": raw["published_at"],
                        "fetched_at": raw["fetched_at"],
                        "source": r["source_id"],
                        "sha256": r["sha256"],
                        "body_chars": len(raw["body"]),
                        "risk": a["risk_level"],
                        "relevance": a["relevance"],
                        "quality": a["quality_flags"],
                        "project_status": raw["project_status"],
                        "capacity": raw["capacity"],
                    }
                )
            for spec in selected:
                sample = next(r for r in real if r["source_id"] == spec["id"])
                response = fetcher.get(sample["raw"]["url"])
                parsed = parse_article(response.text, sample["raw"]["url"], spec["parser"])
                assert parsed["body"] == sample["raw"]["body"] and parsed["title"] == sample["raw"]["title"]
                assert parsed["published_at"] == datetime.fromisoformat(sample["raw"]["published_at"])
                result["source_checks"].append(
                    {
                        "source": spec["id"],
                        "url": sample["raw"]["url"],
                        "actual_html_reparse_equal": True,
                        "response_sha256": hashlib.sha256(response.content).hexdigest(),
                    }
                )
            counts_before = {mode: len(rows(session, mode)) for mode in ["live", "demo", "manual"]}
            for mode in ["live", "demo", "manual"]:
                for kind in ["daily", "weekly"]:
                    report = generate_report(session, mode, kind)
                    target = ROOT / f"runtime/platform/{mode}-{kind}.html"
                    target.write_text(report.html, encoding="utf-8")
                    if mode == "live":
                        assert "DEMO factory" not in report.html
            assert "本期没有" in generate_report(session, "live").html
            historical = generate_report(
                session, "live", "daily", datetime.fromisoformat("2025-07-04T12:00:00+00:00")
            )
            assert "Circular Economy:" in historical.html
            (ROOT / "runtime/platform/live-historical.html").write_text(historical.html, encoding="utf-8")
            assert counts_before == {mode: len(rows(session, mode)) for mode in counts_before}
            result["namespace_counts"] = counts_before
            result["relevance_counts"] = dict(Counter(r["analysis"]["relevance"] for r in real))
            states = snapshots(session, "live")
            assert len(states) == 12 and all(s["state"] == "unknown" for s in states.values())
            result["port_live_states"] = {k: v["state"] for k, v in states.items()}
            result["source_last_success"] = {
                s.id: s.last_success_at for s in session.scalars(select(PlatformSource))
            }
            result["real_records"] = len(real)
            result["current_qualified_operations"] = 0
            result["reports"] = (
                "PASS: today empty with coverage caveat; historical dated report includes actual policy; six scoped daily/weekly HTML generated"
            )
            result["status"] = (
                "PARTIAL: transport/storage/UI-ready real chain; no qualified current operational or price/enterprise production evidence"
            )
        result["robots"] = fetcher.robots_audit
    finally:
        fetcher.close()
    output = ROOT / "docs/platform/LIVE_EVIDENCE.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "real_records": result["real_records"],
                "relevance": result["relevance_counts"],
                "output": str(output),
            }
        )
    )


if __name__ == "__main__":
    main()
