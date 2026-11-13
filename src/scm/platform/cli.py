"""Local commands; collect --due can be invoked by an explicitly configured task scheduler."""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from scm.database.session import session_factory
from scm.platform.adapters import collect, import_file
from scm.platform.demo import seed
from scm.platform.models import PlatformSource
from scm.platform.service import generate_report, register, specs
from scm.settings import utcnow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default="sqlite:///runtime/platform/platform.db")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("demo")
    fetch = sub.add_parser("collect")
    fetch.add_argument("--source", action="append")
    fetch.add_argument("--due", action="store_true")
    load = sub.add_parser("import-file")
    load.add_argument("file", type=Path)
    report = sub.add_parser("report")
    report.add_argument("--mode", choices=["live", "demo", "manual"], required=True)
    report.add_argument("--kind", choices=["daily", "weekly"], default="daily")
    report.add_argument("--output", type=Path, required=True)
    decision = sub.add_parser("decisions")
    decision.add_argument("--mode", choices=["live", "demo", "manual"], required=True)
    business = sub.add_parser("import-links")
    business.add_argument("file", type=Path)
    business.add_argument("--mode", choices=["live", "demo", "manual"], required=True)
    business.add_argument("--actor", required=True)
    business.add_argument("--reason", required=True)
    support = sub.add_parser("decision-report")
    support.add_argument("--mode", choices=["live", "demo", "manual"], required=True)
    support.add_argument("--kind", choices=["daily", "weekly"], default="weekly")
    support.add_argument("--output", type=Path, required=True)
    update = sub.add_parser("update")
    update.add_argument("--source", action="append")
    update.add_argument("--output-dir", type=Path, default=Path("runtime/platform/updates"))
    notices = sub.add_parser("import-notice-metadata")
    notices.add_argument("file", type=Path)
    notices.add_argument("--actor", required=True)
    notices.add_argument("--reason", required=True)
    diesel = sub.add_parser("import-diesel")
    diesel.add_argument("file", type=Path)
    diesel.add_argument("--actor", required=True)
    diesel.add_argument("--reason", required=True)
    sub.add_parser("source-health")
    args = parser.parse_args()
    factory = session_factory(args.database_url)
    with factory.begin() as session:
        register(session)
    if args.command == "init":
        result = {"status": "initialized", "database": args.database_url}
    elif args.command == "demo":
        result = seed(factory)
    elif args.command == "import-file":
        result = import_file(factory, args.file.read_bytes(), args.file.name)
    elif args.command == "collect":
        selected = specs()
        if args.source:
            if set(args.source) - {s["id"] for s in selected}:
                parser.error("Unknown source id")
            selected = [s for s in selected if s["id"] in args.source]
        if args.due:
            with factory() as session:
                latest = {s.id: s.last_checked_at for s in session.scalars(select(PlatformSource))}
            selected = [
                s
                for s in selected
                if s.get("enabled")
                and (
                    not latest.get(s["id"])
                    or datetime.fromisoformat(latest[s["id"]]) + timedelta(minutes=s["frequency_minutes"])
                    <= utcnow()
                )
            ]
        result = collect(factory, selected)
    elif args.command == "decisions":
        from scm.platform.decision import refresh

        with factory.begin() as session:
            result = refresh(session, args.mode)
    elif args.command == "import-links":
        from scm.platform.decision_io import import_links

        result = import_links(
            factory, args.file.read_bytes(), args.file.name, args.mode, args.actor, args.reason
        )
    elif args.command == "decision-report":
        from scm.platform.decision_io import decision_report

        with factory.begin() as session:
            saved = decision_report(session, args.mode, args.kind)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(saved.html, encoding="utf-8")
            result = {"report_id": saved.id, "output": str(args.output)}
    elif args.command == "import-notice-metadata":
        from scm.platform.manual_metadata import load

        result = load(factory, args.file.read_bytes(), args.actor, args.reason)
    elif args.command == "import-diesel":
        from scm.platform.diesel_import import load

        result = load(factory, args.file.read_bytes(), args.file.name, args.actor, args.reason)
    elif args.command == "source-health":
        from scm.platform.decision_io import source_health

        with factory.begin() as session:
            result = source_health(session)
    elif args.command == "update":
        from scm.platform.automation import update

        result = update(factory, args.output_dir, args.source)
    else:
        with factory.begin() as session:
            saved = generate_report(session, args.mode, args.kind)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(saved.html, encoding="utf-8")
            result = {"report_id": saved.id, "output": str(args.output), "mode": args.mode}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if args.command == "update" and any(
        r.get("status") in ["failed", "unavailable"] for r in result["collection"]
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
