"""summary quality and processing errors

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("meetings", sa.Column("processing_error", sa.Text(), nullable=True))
    op.add_column(
        "meeting_ai_outputs",
        sa.Column("quality_json", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("meeting_ai_outputs", "quality_json")
    op.drop_column("meetings", "processing_error")
