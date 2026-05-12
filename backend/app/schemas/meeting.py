from datetime import datetime
from pydantic import BaseModel


class MeetingCreate(BaseModel):
    workspace_id: int
    title: str
    source_type: str = "transcript"
    meeting_date: datetime | None = None


class TranscriptIn(BaseModel):
    transcript_text: str


class MeetingOut(BaseModel):
    id: int
    workspace_id: int
    title: str
    source_type: str
    status: str
    transcript_text: str | None

    class Config:
        from_attributes = True


class MeetingAIOutputOut(BaseModel):
    meeting_id: int
    provider: str
    model: str
    summary_json: dict


class ActionItemUpdate(BaseModel):
    task: str | None = None
    owner: str | None = None
    due_date: str | None = None
    priority: str | None = None
    status: str | None = None
    evidence: str | None = None
