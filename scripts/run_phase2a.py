"""Run bounded, permission-gated Phase 2A; no UI or LLM/API calls.

Usage: timeout 180s python scripts/run_phase2a.py --database-url sqlite:///runtime/phase2a/live.db
"""

import argparse
import json
from datetime import date
from pathlib import Path

from scm.content.digest import generate_digest
from scm.content.service import collect_content
from scm.database.session import session_factory
from scm.settings import ROOT, TIMEZONE, utcnow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default="sqlite:///runtime/phase2a/live.db")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runtime/phase2a")
    parser.add_argument("--day", type=date.fromisoformat)
    args = parser.parse_args()
    specs = json.loads((ROOT / "config/phase2a_sources.json").read_text())
    factory = session_factory(args.database_url)
    results = collect_content(factory, specs)
    day = args.day or utcnow().astimezone(TIMEZONE).date()
    with factory() as session:
        html, summary = generate_digest(session, day)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "daily.html").write_text(html, encoding="utf-8")
    payload = {
        "verification_type": "LIVE_HTTP",
        "completed_at": utcnow().isoformat(),
        "results": results,
        "digest": summary,
    }
    (args.output_dir / "run.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
