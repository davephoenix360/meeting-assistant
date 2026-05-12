"""init

Revision ID: 0001
Revises: 
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('email', sa.String(255), unique=True), sa.Column('name', sa.String(255)), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table('workspaces', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('name', sa.String(255)), sa.Column('owner_user_id', sa.Integer(), sa.ForeignKey('users.id')), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table('workspace_members', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspaces.id')), sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id')), sa.Column('role', sa.String(64)))
    op.create_table('meetings', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspaces.id')), sa.Column('title', sa.String(255)), sa.Column('source_type', sa.Enum('upload','transcript','zoom','google_meet','teams', name='sourcetype')), sa.Column('meeting_date', sa.DateTime(timezone=True), nullable=True), sa.Column('status', sa.Enum('created','uploaded','transcribing','transcribed','summarizing','completed','failed', name='meetingstatus')), sa.Column('audio_file_path', sa.String(512), nullable=True), sa.Column('video_file_path', sa.String(512), nullable=True), sa.Column('transcript_text', sa.Text(), nullable=True), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table('meeting_ai_outputs', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id'), unique=True), sa.Column('provider', sa.String(64)), sa.Column('model', sa.String(128)), sa.Column('summary_json', sa.JSON()), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table('action_items', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id')), sa.Column('task', sa.Text()), sa.Column('owner', sa.String(255), nullable=True), sa.Column('due_date', sa.String(64), nullable=True), sa.Column('priority', sa.String(16)), sa.Column('status', sa.String(32)), sa.Column('evidence', sa.Text()), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))

def downgrade():
    op.drop_table('action_items'); op.drop_table('meeting_ai_outputs'); op.drop_table('meetings'); op.drop_table('workspace_members'); op.drop_table('workspaces'); op.drop_table('users')
