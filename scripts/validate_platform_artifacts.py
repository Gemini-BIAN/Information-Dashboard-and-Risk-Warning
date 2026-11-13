"""Offline verification of actual response bytes captured by the approved Live adapters."""

import hashlib
import json
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from sqlalchemy import select

from scm.collectors.parsers import parse_article
from scm.database.session import session_factory
from scm.platform.models import Audit
from scm.platform.service import rows, specs
from scm.settings import ROOT, utcnow


def main():
    factory = session_factory("sqlite:///runtime/platform/platform.db")
    checks = []
    configured = {s["id"]: s for s in specs()}
    with factory() as session:
        for r in rows(session, "live"):
            log = session.scalar(
                select(Audit)
                .where(Audit.source_id == r["source_id"], Audit.mode == "live")
                .order_by(Audit.id.desc())
            )
            payload = json.loads(log.payload_json)
            assert payload["verification_type"] == "LIVE_HTTP"

            def matches(a):
                if a["url"] == r["raw"]["url"]:
                    return True
                file = ROOT / "runtime/platform/artifacts" / a["path"]
                soup = BeautifulSoup(file.read_bytes(), "html.parser")
                canonical = soup.find("link", rel="canonical")
                return bool(canonical and urljoin(a["url"], canonical.get("href", "")) == r["raw"]["url"])

            artifact = next(a for a in payload["captures"] if matches(a))
            assert artifact["mode"] == "live"
            path = ROOT / "runtime/platform/artifacts" / artifact["path"]
            content = path.read_bytes()
            assert (
                len(content) == artifact["bytes"]
                and hashlib.sha256(content).hexdigest() == artifact["sha256"]
            )
            parsed = parse_article(
                content.decode("utf-8"), r["raw"]["url"], configured[r["source_id"]]["parser"]
            )
            assert parsed["body"] == r["raw"]["body"] and parsed["title"] == r["raw"]["title"]
            checks.append(
                {
                    "item_id": r["id"],
                    "url": r["raw"]["url"],
                    "response_sha256": artifact["sha256"],
                    "response_bytes": artifact["bytes"],
                    "path": str(path.relative_to(ROOT)),
                    "raw_body_matches_reparsed_saved_html": True,
                }
            )
    output = ROOT / "docs/platform/RAW_CAPTURE_EVIDENCE.json"
    output.write_text(
        json.dumps(
            {
                "verified_at": utcnow().isoformat(),
                "status": "PASS",
                "actual_saved_articles": len(checks),
                "checks": checks,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("PASS", len(checks), "actual saved HTML articles verified")


if __name__ == "__main__":
    main()
