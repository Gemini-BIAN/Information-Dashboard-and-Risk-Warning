"""Opt-in synthetic records, never called by Live collection/import."""

import json

from scm.platform.contracts import Record
from scm.platform.service import ingest, register
from scm.settings import ROOT, utcnow


def seed(factory):
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    with factory.begin() as session:
        register(
            session,
            [
                {
                    "id": "platform-demo",
                    "name": "DEMO synthetic records",
                    "adapter": "fixture",
                    "url": "https://example.invalid/demo",
                    "automatic_access_allowed": False,
                }
            ],
        )
        for raw in json.loads((ROOT / "fixtures/platform/demo.json").read_text(encoding="utf-8")):
            rec = Record.model_validate({**raw, "fetched_at": utcnow()})
            outcome, _ = ingest(session, "platform-demo", rec)
            counts[outcome] += 1
    # Reuse existing Module01 explicit Demo service; its Live state is never touched.
    from scm.ports.demo import seed as seed_ports

    seed_ports(factory)
    return counts
