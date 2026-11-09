"""Additive Module01 identity/state and in-app notification tables; preserve existing evidence."""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "port_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("data_mode", sa.String(), nullable=False),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.UniqueConstraint("source_id", "external_id", "data_mode"),
    )
    op.create_table(
        "port_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("signal_id", sa.Integer(), sa.ForeignKey("port_signals.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("data_mode", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("read_at", sa.String(), nullable=True),
        sa.Column("summary_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("signal_id", "version"),
    )


def downgrade():
    op.drop_table("port_alerts")
    op.drop_table("port_signals")
