"""calendar foundation

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "calendar_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("account_email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="connected"),
        sa.Column("scopes_json", sa.JSON(), nullable=True),
        sa.Column("provider_metadata_json", sa.JSON(), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column(
            "calendar_account_id",
            sa.Integer(),
            sa.ForeignKey("calendar_accounts.id"),
            nullable=False,
        ),
        sa.Column("external_event_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organizer_email", sa.String(255), nullable=True),
        sa.Column("meeting_url", sa.String(1024), nullable=True),
        sa.Column("location", sa.String(512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("attendees_json", sa.JSON(), nullable=True),
        sa.Column("artifacts_json", sa.JSON(), nullable=True),
        sa.Column("imported_meeting_id", sa.Integer(), sa.ForeignKey("meetings.id"), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_calendar_accounts_workspace_provider_email",
        "calendar_accounts",
        ["workspace_id", "provider", "account_email"],
    )
    op.create_index(
        "ix_calendar_events_account_external",
        "calendar_events",
        ["calendar_account_id", "external_event_id"],
        unique=True,
    )
    op.create_index(
        "ix_calendar_events_workspace_starts_at",
        "calendar_events",
        ["workspace_id", "starts_at"],
    )


def downgrade():
    op.drop_index("ix_calendar_events_workspace_starts_at", table_name="calendar_events")
    op.drop_index("ix_calendar_events_account_external", table_name="calendar_events")
    op.drop_index(
        "ix_calendar_accounts_workspace_provider_email",
        table_name="calendar_accounts",
    )
    op.drop_table("calendar_events")
    op.drop_table("calendar_accounts")
