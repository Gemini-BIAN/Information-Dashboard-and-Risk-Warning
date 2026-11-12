"""Add evidence-bound decision cards; no changes to immutable source evidence."""

import sqlalchemy as sa
from alembic import op

revision = "005_decision"
down_revision = "004_platform"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "decision_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "evidence_id", sa.Integer(), sa.ForeignKey("platform_evidence.id"), unique=True, nullable=False
        ),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
    )


def downgrade():
    op.drop_table("decision_cards")
