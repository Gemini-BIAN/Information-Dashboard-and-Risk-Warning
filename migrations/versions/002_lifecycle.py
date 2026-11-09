"""Evidence-based policy/operational state and source success telemetry."""

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    for name in ["expiry_at", "repeal_at"]:
        op.add_column("events", sa.Column(name, sa.String(), nullable=True))
    for name, default in [
        ("policy_reasons_json", "[]"),
        ("lifecycle", "unknown"),
        ("lifecycle_reasons_json", "[]"),
        ("port_signals_json", "{}"),
        ("rule_version", "legacy"),
        ("source_confidence", "unreviewed"),
    ]:
        op.add_column("events", sa.Column(name, sa.Text(), nullable=False, server_default=default))
    op.add_column("sources", sa.Column("last_success_at", sa.String(), nullable=True))


def downgrade():
    op.drop_column("sources", "last_success_at")
    for name in [
        "expiry_at",
        "repeal_at",
        "policy_reasons_json",
        "lifecycle",
        "lifecycle_reasons_json",
        "port_signals_json",
        "rule_version",
        "source_confidence",
    ]:
        op.drop_column("events", name)
