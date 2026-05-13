from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class TagMixin(BaseModel):
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags", mode="before")
    @classmethod
    def default_tags(cls, value):
        return value or []


class MeetingCreate(TagMixin):
    workspace_id: int
    title: str
    source_type: str = "transcript"
    meeting_date: datetime | None = None


class MeetingTagsUpdate(TagMixin):
    pass


class TranscriptIn(BaseModel):
    transcript_text: str


class MeetingOut(TagMixin):
    id: int
    workspace_id: int
    title: str
    source_type: str
    status: str
    transcript_text: str | None
    audio_file_path: str | None = None
    video_file_path: str | None = None
    transcript_source: str | None = None
    transcript_provider: str | None = None
    transcript_model: str | None = None
    transcript_language: str | None = None
    transcript_confidence: str | None = None
    transcript_created_at: datetime | None = None
    processing_error: str | None = None

    class Config:
        from_attributes = True


class MeetingAIOutputOut(BaseModel):
    meeting_id: int
    provider: str
    model: str
    summary_json: dict
    quality_json: dict | None = None


class MeetingSavedViewCreate(BaseModel):
    workspace_id: int = 1
    name: str
    filters: dict = Field(default_factory=dict)


class MeetingSavedViewOut(BaseModel):
    id: int
    workspace_id: int
    name: str
    filters: dict
    created_at: datetime


class MeetingSummaryUpdate(BaseModel):
    title: str | None = None
    executive_summary: str | None = None
    key_points: list[str] | None = None
    risks_blockers: list[str] | None = None
    open_questions: list[str] | None = None
    follow_up_email: str | None = None


class MeetingSummaryRegenerateIn(BaseModel):
    section: str


class ActionItemUpdate(BaseModel):
    task: str | None = None
    owner: str | None = None
    due_date: str | None = None
    priority: str | None = None
    status: str | None = None
    evidence: str | None = None


class ActionItemCreate(BaseModel):
    meeting_id: int
    task: str
    owner: str | None = None
    due_date: str | None = None
    priority: str = "medium"
    evidence: str = ""


class ActionItemOut(BaseModel):
    id: int
    meeting_id: int
    meeting_title: str
    task: str
    owner: str | None
    due_date: str | None
    priority: str
    status: str
    evidence: str
    created_at: datetime
    archived_at: datetime | None = None


class SearchResultOut(BaseModel):
    kind: str
    meeting_id: int
    meeting_title: str
    title: str
    excerpt: str
    status: str | None = None


class RelatedMeetingOut(BaseModel):
    meeting_id: int
    meeting_title: str
    status: str
    source_type: str
    tags: list[str] = Field(default_factory=list)
    score: int
    reasons: list[str]
    excerpt: str


class MeetingCalendarEventOut(BaseModel):
    id: int
    calendar_account_id: int
    external_event_id: str
    title: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    organizer_email: str | None = None
    meeting_url: str | None = None
    location: str | None = None
    description: str | None = None
    attendees: list[dict] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)


class TranscriptionProviderStatusOut(BaseModel):
    provider: str
    mode: str
    ready: bool
    can_transcribe: bool
    label: str
    message: str
    model: str | None = None
    device: str | None = None
    compute_type: str | None = None
    package_installed: bool | None = None
