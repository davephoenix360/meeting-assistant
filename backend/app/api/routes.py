from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import Meeting, MeetingStatus, MeetingAIOutput, ActionItem
from app.schemas.meeting import (
    MeetingCreate,
    MeetingOut,
    TranscriptIn,
    MeetingAIOutputOut,
    ActionItemUpdate,
)
from app.core.config import settings
from app.services.llm.openrouter_provider import OpenRouterProvider
from app.services.summarization.meeting_summarizer import MeetingSummarizer
from app.jobs.process_meeting import process_meeting
from app.services.llm.base import LLMProviderError
import os

router = APIRouter(prefix="/api")


@router.post("/meetings", response_model=MeetingOut)
def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db)):
    meeting = Meeting(**payload.model_dump())
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.get("/meetings", response_model=list[MeetingOut])
def list_meetings(db: Session = Depends(get_db)):
    return db.query(Meeting).order_by(Meeting.id.desc()).all()


@router.get("/meetings/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404)
    return meeting


@router.post("/meetings/{meeting_id}/upload")
async def upload_file(
    meeting_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404)
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, f"{meeting_id}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(await file.read())
    if file.content_type and file.content_type.startswith("audio"):
        meeting.audio_file_path = file_path
    else:
        meeting.video_file_path = file_path
    meeting.status = MeetingStatus.uploaded
    db.commit()
    return {"ok": True, "path": file_path}


@router.post("/meetings/{meeting_id}/transcript", response_model=MeetingOut)
def set_transcript(
    meeting_id: int, payload: TranscriptIn, db: Session = Depends(get_db)
):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404)
    meeting.transcript_text = payload.transcript_text
    meeting.status = MeetingStatus.transcribed
    db.commit()
    db.refresh(meeting)
    return meeting


@router.post("/meetings/{meeting_id}/process")
async def process(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404)
    if not meeting.transcript_text:
        raise HTTPException(400, "Transcript required for MVP")
    llm = OpenRouterProvider(settings.openrouter_api_key or "")
    summarizer = MeetingSummarizer(llm, settings.openrouter_default_model)
    try:
        await process_meeting(
            meeting, db, summarizer, "openrouter", settings.openrouter_default_model
        )
        return {"ok": True}
    except LLMProviderError as e:
        status = e.status_code or 502
        # Preserve rate limiting semantics for the frontend.
        if status == 429:
            raise HTTPException(429, "Rate limited by OpenRouter. Try again in a bit.")
        raise HTTPException(status, e.message)


@router.get("/meetings/{meeting_id}/ai-output", response_model=MeetingAIOutputOut)
def get_ai_output(meeting_id: int, db: Session = Depends(get_db)):
    out = db.query(MeetingAIOutput).filter_by(meeting_id=meeting_id).first()
    if not out:
        raise HTTPException(404)
    return out


@router.patch("/action-items/{action_item_id}")
def patch_action_item(
    action_item_id: int, payload: ActionItemUpdate, db: Session = Depends(get_db)
):
    item = db.get(ActionItem, action_item_id)
    if not item:
        raise HTTPException(404)
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.get("/meetings/{meeting_id}/export/markdown", response_class=PlainTextResponse)
def export_markdown(meeting_id: int, db: Session = Depends(get_db)):
    out = db.query(MeetingAIOutput).filter_by(meeting_id=meeting_id).first()
    if not out:
        raise HTTPException(404)
    s = out.summary_json
    md = f"# {s['title']}\n\n## Executive Summary\n{s['executive_summary']}\n\n## Action Items\n"
    for a in s.get("action_items", []):
        md += f"- [ ] {a['task']} ({a.get('owner') or 'Unassigned'})\n"
    return md
