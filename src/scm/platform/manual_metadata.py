"""Rights-compliant user-authored notice summaries; no HTTP and no Live promotion."""

import json

from scm.platform.contracts import Record
from scm.platform.service import audit, ingest, register
from scm.settings import utcnow


def load(factory, content, actor, reason):
    if len(content) > 2_000_000 or not actor.strip() or not reason.strip():
        raise ValueError("File <=2MB, actor and reason required")
    values = json.loads(content.decode("utf-8-sig"))
    if not isinstance(values, list) or not 1 <= len(values) <= 1000:
        raise ValueError("1–1000 metadata notices required")
    records = []
    for row in values:
        row = dict(row)
        if row.pop("rights_basis", None) != "user_authored_summary":
            raise ValueError("Only user-authored summaries, not restricted source body copies")
        summary = row.pop("summary")
        records.append(
            Record.model_validate(
                {
                    **row,
                    "body": summary,
                    "module": "ports",
                    "mode": "manual",
                    "verification": "MANUAL",
                    "fetched_at": utcnow(),
                }
            )
        )
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    with factory.begin() as s:
        register(
            s,
            [
                dict(
                    id="manual-notice-metadata",
                    name="User-authored operational metadata",
                    adapter="manual",
                    url="https://example.invalid/metadata",
                    automatic_access_allowed=False,
                )
            ],
        )
        for rec in records:
            outcome, _ = ingest(s, "manual-notice-metadata", rec)
            counts[outcome] += 1
        audit(
            s,
            "manual-notice-metadata",
            "manual",
            {
                "actor": actor,
                "reason": reason,
                "rights_basis": "user_authored_summary",
                "writes": counts,
                "note": "No HTTP, summary is user assertion, not copied official body or verified Live fact",
            },
        )
    return counts
