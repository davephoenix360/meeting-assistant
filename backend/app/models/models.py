import enum
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.session import Base


class SourceType(str, enum.Enum):
    upload = "upload"
    transcript = "transcript"
    zoom = "zoom"
    google_meet = "google_meet"
    teams = "teams"


class MeetingStatus(str, enum.Enum):
    created = "created"
    uploaded = "uploaded"
    transcribing = "transcribing"
    transcribed = "transcribed"
    summarizing = "summarizing"
    completed = "completed"
    failed = "failed"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(64))


class Meeting(Base):
    __tablename__ = "meetings"
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), default=SourceType.transcript)
    meeting_date: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[MeetingStatus] = mapped_column(Enum(MeetingStatus), default=MeetingStatus.created)
    audio_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    video_file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transcript_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transcript_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    transcript_language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transcript_confidence: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transcript_created_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MeetingAIOutput(Base):
    __tablename__ = "meeting_ai_outputs"
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), unique=True)
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    summary_json: Mapped[dict] = mapped_column(JSON)
    quality_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ActionItem(Base):
    __tablename__ = "action_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"))
    task: Mapped[str] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(64), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(32), default="open")
    evidence: Mapped[str] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    archived_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
