import argparse
import json
import logging
from pathlib import Path
from datetime import date
from scm.database.session import session_factory
from scm.collectors.service import register_sources, load_demo, run_collection, write_source_audit
from scm.shipments.service import import_csv
from scm.reports.service import generate_report
from scm.settings import ROOT


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    parser = argparse.ArgumentParser(description='Global Supply Chain Intelligence & Risk Monitor')
    parser.add_argument('--database-url', default=None)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('demo')
    collect = sub.add_parser('collect')
    collect.add_argument('--source', action='append')
    audit = sub.add_parser('audit')
    audit.add_argument('--output', default='SOURCE_AUDIT.md')
    shipments = sub.add_parser('import-shipments')
    shipments.add_argument('file')
    shipments.add_argument('--mode', choices=['demo', 'live'], required=True)
    report = sub.add_parser('report')
    report.add_argument('--kind', choices=['daily', 'weekly'], required=True)
    report.add_argument('--mode', choices=['demo', 'live'], required=True)
    report.add_argument('--day', type=date.fromisoformat)
    report.add_argument('--output')
    sub.add_parser('schedule')
    args = parser.parse_args()
    factory = session_factory(args.database_url) if args.database_url else session_factory()
    with factory.begin() as session:
        specs = register_sources(session)
    if args.command == 'init':
        print('Schema migrated; sources registered. No demo data loaded.')
    elif args.command == 'demo':
        print(json.dumps(load_demo(factory)))
        with factory.begin() as session:
            print(import_csv(session, (ROOT / 'fixtures/demo_shipments.csv').read_text(encoding='utf-8'), 'demo'))
    elif args.command == 'collect':
        selected = [s for s in specs if not args.source or s['id'] in args.source]
        if not selected or (args.source and set(args.source) - {s['id'] for s in specs}):
            parser.error('Unknown source id')
        print(json.dumps(run_collection(factory, selected), ensure_ascii=False, indent=2))
    elif args.command == 'audit':
        write_source_audit(factory, Path(args.output))
    elif args.command == 'import-shipments':
        with factory.begin() as session:
            print(import_csv(session, Path(args.file).read_text(encoding='utf-8-sig'), args.mode))
    elif args.command == 'report':
        with factory.begin() as session:
            row = generate_report(session, args.kind, args.mode, args.day)
            if args.output:
                Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                Path(args.output).write_text(row.html, encoding='utf-8')
            print(f'Report saved: id={row.id}, mode={row.data_mode}, kind={row.kind}')
    else:
        from scm.scheduler import run_scheduler
        run_scheduler(factory)


if __name__ == '__main__':
    main()
