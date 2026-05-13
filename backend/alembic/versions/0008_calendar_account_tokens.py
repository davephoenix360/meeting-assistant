"""calendar account tokens

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "calendar_account_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "calendar_account_id",
            sa.Integer(),
            sa.ForeignKey("calendar_accounts.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("token_type", sa.String(64), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes_json", sa.JSON(), nullable=True),
        sa.Column("provider_token_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("calendar_account_tokens")
