from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from app.db.session import get_db
from app.models.models import Meeting, MeetingStatus, MeetingAIOutput, ActionItem
from app.schemas.meeting import (
    MeetingCreate,
    MeetingOut,
    TranscriptIn,
    MeetingAIOutputOut,
    MeetingSummaryUpdate,
    ActionItemCreate,
    ActionItemUpdate,
    ActionItemOut,
)
from app.schemas.summary import MeetingSummarySchema
from app.core.config import settings
from app.services.summarization.meeting_summarizer import MeetingSummarizer
from app.jobs.process_meeting import process_meeting
from app.services.llm.base import LLMProviderError
from app.services.llm.factory import get_llm_provider
from app.services.transcription.base import TranscriptionProviderError
from app.services.transcription.factory import get_transcription_provider
import os

router = APIRouter(prefix="/api")


def action_item_out(item: ActionItem, meeting_title: str) -> ActionItemOut:
    return ActionItemOut(
        id=item.id,
        meeting_id=item.meeting_id,
        meeting_title=meeting_title,
        task=item.task,
        owner=item.owner,
        due_date=item.due_date,
        priority=item.priority,
        status=item.status,
        evidence=item.evidence,
        created_at=item.created_at,
    )


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
    filename = os.path.basename(file.filename or "upload")
    file_path = os.path.join(settings.upload_dir, f"{meeting_id}_{filename}")
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
    meeting.transcript_source = "paste"
    meeting.transcript_provider = "manual"
    meeting.transcript_model = None
    meeting.transcript_language = None
    meeting.transcript_confidence = None
    meeting.transcript_created_at = func.now()
    meeting.status = MeetingStatus.transcribed
    db.commit()
    db.refresh(meeting)
    return meeting


@router.post("/meetings/{meeting_id}/transcribe", response_model=MeetingOut)
async def transcribe_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404)

    file_path = meeting.audio_file_path or meeting.video_file_path
    if not file_path:
        raise HTTPException(400, "Uploaded audio or video required")
    if not os.path.exists(file_path):
        raise HTTPException(404, "Uploaded file could not be found")

    try:
        provider_name, provider = get_transcription_provider()
    except ValueError as e:
        raise HTTPException(500, str(e))

    meeting.status = MeetingStatus.transcribing
    db.commit()

    try:
        result = await provider.transcribe(file_path)
        meeting.transcript_text = result.text
        meeting.transcript_source = "upload"
        meeting.transcript_provider = provider_name
        meeting.transcript_model = result.model
        meeting.transcript_language = result.language
        meeting.transcript_confidence = (
            f"{result.confidence:.4f}" if result.confidence is not None else None
        )
        meeting.transcript_created_at = func.now()
        meeting.status = MeetingStatus.transcribed
        db.commit()
        db.refresh(meeting)
        return meeting
    except TranscriptionProviderError as e:
        meeting.status = MeetingStatus.failed
        db.commit()
        raise HTTPException(
            e.status_code or 502,
            f"{e.provider or provider_name} transcription failed: {e.message}",
        )
    except Exception as e:
        meeting.status = MeetingStatus.failed
        db.commit()
        raise HTTPException(502, f"{provider_name} transcription failed: {e}")


@router.post("/meetings/{meeting_id}/process")
async def process(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404)
    if not meeting.transcript_text:
        raise HTTPException(400, "Transcript required for MVP")
    try:
        provider_name, model, llm = get_llm_provider()
    except ValueError as e:
        raise HTTPException(500, str(e))
    summarizer = MeetingSummarizer(llm, model)
    try:
        await process_meeting(meeting, db, summarizer, provider_name, model)
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


@router.patch(
    "/meetings/{meeting_id}/ai-output/summary", response_model=MeetingAIOutputOut
)
def patch_meeting_summary(
    meeting_id: int, payload: MeetingSummaryUpdate, db: Session = Depends(get_db)
):
    out = db.query(MeetingAIOutput).filter_by(meeting_id=meeting_id).first()
    if not out:
        raise HTTPException(404)

    next_summary = {**out.summary_json, **payload.model_dump(exclude_unset=True)}
    try:
        validated = MeetingSummarySchema.model_validate(next_summary)
    except Exception as e:
        raise HTTPException(400, f"Invalid summary update: {e}")

    out.summary_json = validated.model_dump()
    db.commit()
    db.refresh(out)
    return out


@router.get("/action-items", response_model=list[ActionItemOut])
def list_action_items(status: str | None = None, db: Session = Depends(get_db)):
    query = (
        db.query(ActionItem, Meeting.title.label("meeting_title"))
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .order_by(ActionItem.created_at.desc(), ActionItem.id.desc())
    )
    if status:
        query = query.filter(ActionItem.status == status)

    return [action_item_out(item, meeting_title) for item, meeting_title in query.all()]


@router.post("/action-items", response_model=ActionItemOut)
def create_action_item(payload: ActionItemCreate, db: Session = Depends(get_db)):
    meeting = db.get(Meeting, payload.meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")

    task = payload.task.strip()
    if not task:
        raise HTTPException(400, "Task is required")

    item = ActionItem(
        meeting_id=meeting.id,
        task=task,
        owner=payload.owner.strip() if payload.owner else None,
        due_date=payload.due_date.strip() if payload.due_date else None,
        priority=payload.priority or "medium",
        status="open",
        evidence=payload.evidence.strip() if payload.evidence else "",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return action_item_out(item, meeting.title)


@router.patch("/action-items/{action_item_id}")
def patch_action_item(
    action_item_id: int, payload: ActionItemUpdate, db: Session = Depends(get_db)
):
    item = db.get(ActionItem, action_item_id)
    if not item:
        raise HTTPException(404)
    for k, v in payload.model_dump(exclude_unset=True).items():
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
    md = f"# {s['title']}\n\n## Executive Summary\n{s['executive_summary']}\n\n"
    if s.get("key_points"):
        md += "## Key Points\n"
        for point in s.get("key_points", []):
            md += f"- {point}\n"
        md += "\n"
    if s.get("decisions"):
        md += "## Decisions\n"
        for decision in s.get("decisions", []):
            md += f"- {decision['decision']}"
            if decision.get("owner"):
                md += f" ({decision['owner']})"
            if decision.get("context"):
                md += f": {decision['context']}"
            md += "\n"
        md += "\n"
    md += "## Action Items\n"
    for a in s.get("action_items", []):
        md += f"- [ ] {a['task']} ({a.get('owner') or 'Unassigned'})\n"
    md += "\n"
    if s.get("deliverables"):
        md += "## Deliverables\n"
        for deliverable in s.get("deliverables", []):
            md += f"- {deliverable['deliverable']} ({deliverable.get('owner') or 'Unassigned'})\n"
        md += "\n"
    if s.get("risks_blockers"):
        md += "## Risks and Blockers\n"
        for risk in s.get("risks_blockers", []):
            md += f"- {risk}\n"
        md += "\n"
    if s.get("open_questions"):
        md += "## Open Questions\n"
        for question in s.get("open_questions", []):
            md += f"- {question}\n"
        md += "\n"
    if s.get("follow_up_email"):
        md += f"## Follow-up Email\n{s['follow_up_email']}\n"
    return md
