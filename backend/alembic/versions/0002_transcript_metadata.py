"""transcript metadata

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("meetings", sa.Column("transcript_source", sa.String(64), nullable=True))
    op.add_column("meetings", sa.Column("transcript_provider", sa.String(64), nullable=True))
    op.add_column("meetings", sa.Column("transcript_model", sa.String(128), nullable=True))
    op.add_column("meetings", sa.Column("transcript_language", sa.String(32), nullable=True))
    op.add_column("meetings", sa.Column("transcript_confidence", sa.String(32), nullable=True))
    op.add_column(
        "meetings",
        sa.Column("transcript_created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("meetings", "transcript_created_at")
    op.drop_column("meetings", "transcript_confidence")
    op.drop_column("meetings", "transcript_language")
    op.drop_column("meetings", "transcript_model")
    op.drop_column("meetings", "transcript_provider")
    op.drop_column("meetings", "transcript_source")
