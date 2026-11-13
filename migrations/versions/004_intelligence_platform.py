"""Add unified platform tables; independent of paused regulatory branch."""

import sqlalchemy as sa
from alembic import op

revision = "004_platform"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    tables = {
        "platform_sources": [
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("spec_json", sa.Text(), nullable=False),
            sa.Column("last_checked_at", sa.String()),
            sa.Column("last_success_at", sa.String()),
            sa.Column("status", sa.String(), nullable=False),
        ],
        "platform_items": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_id", sa.String(), sa.ForeignKey("platform_sources.id"), nullable=False),
            sa.Column("external_id", sa.String(), nullable=False),
            sa.Column("mode", sa.String(), nullable=False),
            sa.Column("module", sa.String(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("review_status", sa.String(), nullable=False),
            sa.Column("updated_at", sa.String(), nullable=False),
            sa.UniqueConstraint("source_id", "external_id", "mode"),
        ],
        "platform_evidence": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("item_id", sa.Integer(), sa.ForeignKey("platform_items.id"), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("raw_json", sa.Text(), nullable=False),
            sa.Column("sha256", sa.String(), nullable=False),
            sa.Column("captured_at", sa.String(), nullable=False),
            sa.UniqueConstraint("item_id", "version"),
        ],
        "platform_assessments": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "evidence_id",
                sa.Integer(),
                sa.ForeignKey("platform_evidence.id"),
                nullable=False,
                unique=True,
            ),
            sa.Column("analyzed_at", sa.String(), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
        ],
        "platform_alerts": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "evidence_id",
                sa.Integer(),
                sa.ForeignKey("platform_evidence.id"),
                nullable=False,
                unique=True,
            ),
            sa.Column("mode", sa.String(), nullable=False),
            sa.Column("state", sa.String(), nullable=False),
            sa.Column("created_at", sa.String(), nullable=False),
        ],
        "platform_audits": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_id", sa.String(), nullable=False),
            sa.Column("mode", sa.String(), nullable=False),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
        ],
        "platform_reviews": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("item_id", sa.Integer(), sa.ForeignKey("platform_items.id"), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("actor", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
        ],
        "platform_reports": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("mode", sa.String(), nullable=False),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("period_start", sa.String(), nullable=False),
            sa.Column("generated_at", sa.String(), nullable=False),
            sa.Column("html", sa.Text(), nullable=False),
            sa.UniqueConstraint("mode", "kind", "period_start"),
        ],
    }
    for name, columns in tables.items():
        op.create_table(name, *columns)


def downgrade():
    for name in ["reports", "reviews", "audits", "alerts", "assessments", "evidence", "items", "sources"]:
        op.drop_table("platform_" + name)
