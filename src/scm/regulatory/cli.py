import argparse
import json
from pathlib import Path

from sqlalchemy import select

from scm.database.session import session_factory
from scm.regulatory.manifest import input_status, load_manifest
from scm.regulatory.models import RegulationDocument
from scm.regulatory.parsing import parse_document
from scm.regulatory.retrieval import answer
from scm.regulatory.storage import download, register
from scm.settings import ROOT


def main():
    parser = argparse.ArgumentParser(description="Module02 foundations; no catalog/real legal texts bundled")
    parser.add_argument("--database-url", default="sqlite:///runtime/regulatory/library.db")
    parser.add_argument("--storage", type=Path, default=ROOT / "runtime/regulatory/files")
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("inputs")
    status.add_argument("--directory", type=Path, default=ROOT / "data/regulatory/research")
    imp = sub.add_parser("import-manifest")
    imp.add_argument("file", type=Path)
    work = sub.add_parser("import-work")
    work.add_argument("--directory", type=Path, default=ROOT / "data/regulatory/research")
    work.add_argument("--snapshot", type=Path, default=ROOT / "runtime/regulatory/research-snapshot.json")
    dl = sub.add_parser("download")
    dl.add_argument("--permissions", type=Path, default=ROOT / "config/regulatory/permissions.json")
    dl.add_argument("--celex", action="append")
    parse = sub.add_parser("parse")
    parse.add_argument("document_id")
    ask = sub.add_parser("search")
    ask.add_argument("document_id")
    ask.add_argument("question")
    args = parser.parse_args()
    if args.command == "inputs":
        files = input_status(args.directory)
        print(
            json.dumps(
                {"status": "PASS" if all(f["present"] for f in files) else "BLOCKED", "files": files},
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    factory = session_factory(args.database_url)
    with factory.begin() as session:
        if args.command == "import-work":
            from scm.regulatory.work import import_work

            result = import_work(session, args.directory, args.snapshot)
            print(json.dumps(result["counts"], ensure_ascii=False, indent=2))
        elif args.command == "import-manifest":
            entries = load_manifest(args.file)
            for entry in entries:
                register(session, entry)
            print(json.dumps({"imported": len(entries), "normalized_contract_only": True}))
        elif args.command == "download":
            from scm.regulatory.manifest import ManifestEntry

            permissions = json.loads(args.permissions.read_text())
            rows = list(session.scalars(select(RegulationDocument)))
            if args.celex:
                rows = [r for r in rows if json.loads(r.metadata_json)["celex"] in args.celex]
            results = []
            for row in rows:
                with session.begin_nested():
                    results.append(
                        download(
                            session,
                            ManifestEntry.model_validate_json(row.metadata_json),
                            args.storage,
                            permissions,
                        )
                    )
            print(json.dumps({"targets": len(rows), "results": results}, ensure_ascii=False, indent=2))
        else:
            row = session.get(RegulationDocument, args.document_id)
            if row is None:
                parser.error("Unknown document identity; import actual manifest first")
            if args.command == "parse":
                print(json.dumps(parse_document(session, row, args.storage), ensure_ascii=False, indent=2))
            else:
                print(
                    json.dumps(
                        answer(session, args.question, row.id, args.storage), ensure_ascii=False, indent=2
                    )
                )


if __name__ == "__main__":
    main()
