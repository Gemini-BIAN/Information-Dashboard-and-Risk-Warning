"""Add isolated regulation artifacts, version-scoped chunks and attempt logs."""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "regulatory_documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("download_status", sa.String(), nullable=False),
        sa.Column("parse_status", sa.String(), nullable=False),
        sa.Column("sha256", sa.String()),
        sa.Column("byte_size", sa.Integer()),
        sa.Column("local_path", sa.Text()),
        sa.Column("downloaded_at", sa.String()),
        sa.Column("verification_type", sa.String()),
        sa.Column("error", sa.Text()),
        sa.Column("quality_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "regulatory_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.String(), sa.ForeignKey("regulatory_documents.id"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("unit_type", sa.String(), nullable=False),
        sa.Column("unit_label", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_start", sa.Integer()),
        sa.Column("page_end", sa.Integer()),
        sa.Column("locator", sa.Text(), nullable=False),
        sa.Column("quality_json", sa.Text(), nullable=False),
        sa.Column("terms_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("document_id", "ordinal"),
    )
    op.create_table(
        "regulatory_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.String(), sa.ForeignKey("regulatory_documents.id"), nullable=False),
        sa.Column("attempted_at", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("regulatory_attempts")
    op.drop_table("regulatory_chunks")
    op.drop_table("regulatory_documents")
