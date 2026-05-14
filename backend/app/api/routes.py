from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
import httpx
from sqlalchemy import String, cast, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from pydantic import ValidationError
from app.db.session import get_db
from app.models.models import (
    Meeting,
    MeetingStatus,
    SourceType,
    MeetingAIOutput,
    MeetingSavedView,
    CalendarAccount,
    CalendarAccountToken,
    CalendarEvent,
    ActionItem,
)
from app.schemas.meeting import (
    MeetingCreate,
    MeetingTagsUpdate,
    MeetingOut,
    TranscriptIn,
    MeetingAIOutputOut,
    MeetingSavedViewCreate,
    MeetingSavedViewOut,
    MeetingSummaryUpdate,
    MeetingSummaryRegenerateIn,
    ActionItemCreate,
    ActionItemUpdate,
    ActionItemOut,
    SearchResultOut,
    RelatedMeetingOut,
    MeetingCalendarEventOut,
    MeetingArtifactMatchOut,
    MeetingArtifactAttachOut,
    TranscriptionProviderStatusOut,
)
from app.schemas.summary import MeetingSummarySchema
from app.schemas.calendar import (
    CalendarAccountCreate,
    CalendarAccountOut,
    CalendarBulkMeetingCreate,
    CalendarBulkMeetingCreateOut,
    CalendarEventCreate,
    CalendarEventMeetingCreate,
    CalendarEventOut,
    CalendarOAuthStartOut,
    CalendarProviderStatusOut,
    CalendarSyncRequest,
    CalendarSyncResultOut,
)
from app.core.config import settings
from app.services.summarization.meeting_summarizer import MeetingSummarizer
from app.services.summarization.meeting_summarizer import REGENERATABLE_SECTIONS
from app.services.summarization.quality import evaluate_summary_quality
from app.jobs.process_meeting import process_meeting
from app.services.llm.base import LLMProviderError
from app.services.llm.factory import get_llm_provider
from app.services.transcription.base import TranscriptionProviderError
from app.services.transcription.factory import (
    get_transcription_provider,
    get_transcription_provider_status,
)
from app.services.calendar.providers import (
    apply_refreshed_calendar_token,
    build_calendar_account_token,
    build_calendar_authorization_url,
    calendar_access_token_needs_refresh,
    exchange_calendar_oauth_code,
    fetch_calendar_account_profile,
    fetch_provider_calendar_events,
    list_calendar_provider_statuses,
    refresh_calendar_access_token,
    sync_calendar_account,
)
from app.services.calendar.token_crypto import TokenEncryptionError
import os
import re

router = APIRouter(prefix="/api")

STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "been",
    "before",
    "being",
    "from",
    "have",
    "into",
    "meeting",
    "next",
    "notes",
    "that",
    "their",
    "there",
    "they",
    "this",
    "with",
    "will",
    "would",
    "your",
}


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
        archived_at=item.archived_at,
    )


def search_excerpt(text: str | None, query: str, *, max_length: int = 180) -> str:
    if not text:
        return ""

    normalized = text.replace("\n", " ").strip()
    if not normalized:
        return ""

    index = normalized.lower().find(query.lower())
    if index < 0:
        return normalized[:max_length]

    start = max(0, index - 48)
    end = min(len(normalized), index + len(query) + 132)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(normalized) else ""
    return f"{prefix}{normalized[start:end]}{suffix}"


def normalize_tags(tags: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags or []:
        next_tag = " ".join(str(tag).strip().lower().split())
        if next_tag and next_tag not in seen:
            normalized.append(next_tag[:40])
            seen.add(next_tag)
    return normalized[:12]


def normalize_meeting_filters(filters: dict | None) -> dict:
    filters = filters or {}
    normalized: dict[str, str] = {}
    q = str(filters.get("q") or "").strip()
    status = str(filters.get("status") or "").strip()
    source_type = str(filters.get("source_type") or "").strip()
    tag = str(filters.get("tag") or "").strip()

    if q:
        normalized["q"] = q[:120]
    if status:
        normalized["status"] = status[:32]
    if source_type:
        normalized["source_type"] = source_type[:32]
    tag_values = normalize_tags([tag])
    if tag_values:
        normalized["tag"] = tag_values[0]
    return normalized


def memory_terms(text: str | None, *, limit: int = 90) -> set[str]:
    if not text:
        return set()

    terms: list[str] = []
    for term in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{3,}", text.lower()):
        if term not in STOPWORDS:
            terms.append(term)
    return set(terms[:limit])


def meeting_status_value(meeting: Meeting) -> str:
    return meeting.status.value if hasattr(meeting.status, "value") else str(meeting.status)


def meeting_source_value(meeting: Meeting) -> str:
    return (
        meeting.source_type.value
        if hasattr(meeting.source_type, "value")
        else str(meeting.source_type)
    )


def meeting_memory_blob(
    meeting: Meeting,
    output: MeetingAIOutput | None,
    action_items: list[ActionItem],
) -> str:
    parts = [
        meeting.title,
        " ".join(normalize_tags(meeting.tags)),
        meeting.transcript_text or "",
    ]
    if output:
        parts.append(str(output.summary_json))
    for item in action_items:
        parts.extend([item.task, item.owner or "", item.evidence or ""])
    return " ".join(parts)


def related_excerpt(meeting: Meeting, output: MeetingAIOutput | None) -> str:
    if output and isinstance(output.summary_json, dict):
        summary = output.summary_json.get("executive_summary")
        if summary:
            return str(summary)[:220]
    return search_excerpt(meeting.transcript_text, meeting.title, max_length=220) or meeting.title


def saved_view_out(view: MeetingSavedView) -> MeetingSavedViewOut:
    return MeetingSavedViewOut(
        id=view.id,
        workspace_id=view.workspace_id,
        name=view.name,
        filters=normalize_meeting_filters(view.filters_json),
        created_at=view.created_at,
    )


def calendar_account_out(account: CalendarAccount) -> CalendarAccountOut:
    return CalendarAccountOut(
        id=account.id,
        workspace_id=account.workspace_id,
        provider=account.provider,
        account_email=account.account_email,
        display_name=account.display_name,
        status=account.status,
        scopes=account.scopes_json or [],
        provider_metadata=account.provider_metadata_json or {},
        connected_at=account.connected_at,
        last_sync_at=account.last_sync_at,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def calendar_event_out(event: CalendarEvent) -> CalendarEventOut:
    return CalendarEventOut(
        id=event.id,
        workspace_id=event.workspace_id,
        calendar_account_id=event.calendar_account_id,
        external_event_id=event.external_event_id,
        title=event.title,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        organizer_email=event.organizer_email,
        meeting_url=event.meeting_url,
        location=event.location,
        description=event.description,
        attendees=event.attendees_json or [],
        artifacts=event.artifacts_json or [],
        imported_meeting_id=event.imported_meeting_id,
        raw=event.raw_json or {},
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def meeting_calendar_event_out(event: CalendarEvent) -> MeetingCalendarEventOut:
    return MeetingCalendarEventOut(
        id=event.id,
        calendar_account_id=event.calendar_account_id,
        external_event_id=event.external_event_id,
        title=event.title,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        organizer_email=event.organizer_email,
        meeting_url=event.meeting_url,
        location=event.location,
        description=event.description,
        attendees=event.attendees_json or [],
        artifacts=event.artifacts_json or [],
    )


def upsert_calendar_event(
    db: Session,
    account: CalendarAccount,
    payload: dict,
) -> tuple[CalendarEvent, bool]:
    event = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.calendar_account_id == account.id)
        .filter(CalendarEvent.external_event_id == payload["external_event_id"])
        .first()
    )
    created = event is None
    if event is None:
        event = CalendarEvent(
            workspace_id=account.workspace_id,
            calendar_account_id=account.id,
            external_event_id=payload["external_event_id"],
            title=payload["title"][:255],
        )
        db.add(event)

    event.title = payload["title"][:255]
    event.starts_at = payload.get("starts_at")
    event.ends_at = payload.get("ends_at")
    event.organizer_email = payload.get("organizer_email")
    event.meeting_url = payload.get("meeting_url")
    event.location = payload.get("location")
    event.description = payload.get("description")
    event.attendees_json = payload.get("attendees") or []
    event.artifacts_json = payload.get("artifacts") or []
    event.raw_json = payload.get("raw") or {}
    return event, created


def meeting_source_from_calendar_event(event: CalendarEvent) -> SourceType:
    account = event.raw_json.get("provider") if isinstance(event.raw_json, dict) else None
    event_text = " ".join(
        str(value or "")
        for value in [event.meeting_url, event.location, event.description, account]
    ).lower()
    if "teams.microsoft" in event_text or "teams" in event_text:
        return SourceType.teams
    if "meet.google" in event_text or "google" in event_text:
        return SourceType.google_meet
    if "zoom.us" in event_text or "zoom" in event_text:
        return SourceType.zoom
    return SourceType.upload


def calendar_event_context(event: CalendarEvent) -> str | None:
    lines: list[str] = []
    if event.starts_at:
        lines.append(f"Scheduled: {event.starts_at.isoformat()}")
    if event.organizer_email:
        lines.append(f"Organizer: {event.organizer_email}")
    if event.meeting_url:
        lines.append(f"Meeting URL: {event.meeting_url}")
    if event.location:
        lines.append(f"Location: {event.location}")
    attendees = event.attendees_json or []
    if attendees:
        attendee_values: list[str] = []
        for attendee in attendees[:12]:
            if isinstance(attendee, dict):
                email = attendee.get("email") or attendee.get("address")
                nested = attendee.get("emailAddress")
                if isinstance(nested, dict):
                    email = email or nested.get("address")
                name = attendee.get("displayName") or attendee.get("name")
                attendee_values.append(str(email or name or attendee))
            else:
                attendee_values.append(str(attendee))
        lines.append("Attendees: " + ", ".join(attendee_values))
    if event.description:
        lines.append("Description:")
        lines.append(event.description[:4000])
    return "\n".join(lines) if lines else None


def calendar_event_terms(event: CalendarEvent) -> set[str]:
    attendee_text = " ".join(str(item) for item in event.attendees_json or [])
    artifact_text = " ".join(str(item) for item in event.artifacts_json or [])
    return memory_terms(
        " ".join(
            [
                event.title,
                event.organizer_email or "",
                event.location or "",
                event.description or "",
                event.meeting_url or "",
                attendee_text,
                artifact_text,
            ]
        ),
        limit=80,
    )


def artifact_source_blob(meeting: Meeting) -> str:
    paths = [
        os.path.basename(meeting.audio_file_path or ""),
        os.path.basename(meeting.video_file_path or ""),
    ]
    return " ".join(
        [
            meeting.title,
            " ".join(normalize_tags(meeting.tags)),
            " ".join(paths),
            meeting.transcript_text[:1200] if meeting.transcript_text else "",
        ]
    )


def artifact_match_score(meeting: Meeting, event: CalendarEvent) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    source_terms = memory_terms(artifact_source_blob(meeting), limit=80)
    event_terms = calendar_event_terms(event)
    shared_terms = sorted(source_terms & event_terms)
    if shared_terms:
        score += min(len(shared_terms) * 8, 40)
        reasons.append("Shared terms: " + ", ".join(shared_terms[:5]))

    if meeting.meeting_date and event.starts_at:
        day_delta = abs((meeting.meeting_date.date() - event.starts_at.date()).days)
        if day_delta == 0:
            score += 35
            reasons.append("Same meeting date")
        elif day_delta <= 1:
            score += 20
            reasons.append("Within one day")
        elif day_delta <= 7:
            score += 8
            reasons.append("Within one week")

    source_paths = [
        os.path.basename(meeting.audio_file_path or "").lower(),
        os.path.basename(meeting.video_file_path or "").lower(),
    ]
    artifact_values = " ".join(
        str(value).lower()
        for artifact in event.artifacts_json or []
        for value in artifact.values()
    )
    if any(path and path in artifact_values for path in source_paths):
        score += 30
        reasons.append("Uploaded filename appears in calendar artifacts")

    if event.meeting_url and meeting_source_value(meeting) == "upload":
        score += 6
        reasons.append("Calendar event has a meeting link")

    if event.imported_meeting_id and event.imported_meeting_id != meeting.id:
        score += 5
        reasons.append("Calendar event already has a meeting record")

    return score, reasons[:4]


def copy_artifact_fields(source: Meeting, target: Meeting) -> list[str]:
    copied: list[str] = []
    if source.audio_file_path and not target.audio_file_path:
        target.audio_file_path = source.audio_file_path
        copied.append("audio_file_path")
    if source.video_file_path and not target.video_file_path:
        target.video_file_path = source.video_file_path
        copied.append("video_file_path")
    if source.transcript_text and (
        not target.transcript_text or target.transcript_source == "calendar"
    ):
        target.transcript_text = source.transcript_text
        target.transcript_source = source.transcript_source
        target.transcript_provider = source.transcript_provider
        target.transcript_model = source.transcript_model
        target.transcript_language = source.transcript_language
        target.transcript_confidence = source.transcript_confidence
        target.transcript_created_at = source.transcript_created_at or func.now()
        copied.append("transcript")

    target.tags = normalize_tags(
        (target.tags or []) + (source.tags or []) + ["calendar", "matched-artifact"]
    )
    if target.status != MeetingStatus.completed:
        if target.transcript_text:
            target.status = MeetingStatus.transcribed
        elif target.audio_file_path or target.video_file_path:
            target.status = MeetingStatus.uploaded
    return copied


def create_meeting_record_from_calendar_event(
    db: Session,
    event: CalendarEvent,
    *,
    tags: list[str] | None = None,
) -> tuple[CalendarEvent, bool]:
    if event.imported_meeting_id:
        meeting = db.get(Meeting, event.imported_meeting_id)
        if meeting:
            return event, False
        event.imported_meeting_id = None

    meeting = Meeting(
        workspace_id=event.workspace_id,
        title=event.title,
        source_type=meeting_source_from_calendar_event(event),
        meeting_date=event.starts_at,
        status=MeetingStatus.created,
        tags=normalize_tags((tags or []) + ["calendar"]),
        transcript_text=calendar_event_context(event),
        transcript_source="calendar",
        transcript_provider="calendar",
        transcript_model=None,
        transcript_language=None,
        transcript_confidence=None,
        transcript_created_at=func.now(),
    )
    if meeting.transcript_text:
        meeting.status = MeetingStatus.transcribed

    db.add(meeting)
    db.flush()
    event.imported_meeting_id = meeting.id
    return event, True


def sync_generated_action_items(
    db: Session, meeting_id: int, summary: MeetingSummarySchema
) -> None:
    db.query(ActionItem).filter_by(meeting_id=meeting_id).delete()
    for ai in summary.action_items:
        db.add(
            ActionItem(
                meeting_id=meeting_id,
                task=ai.task,
                owner=ai.owner,
                due_date=ai.due_date,
                priority=ai.priority,
                evidence=ai.evidence,
            )
        )


def build_meeting_summarizer(llm, model: str) -> MeetingSummarizer:
    return MeetingSummarizer(
        llm,
        model,
        refine_threshold_chars=settings.summarization_refine_threshold_chars,
        refine_chunk_chars=settings.summarization_refine_chunk_chars,
        refine_overlap_chars=settings.summarization_refine_overlap_chars,
    )


def preserve_processing_quality_metadata(
    current_quality: dict | None,
    next_quality: dict,
) -> dict:
    processing = (current_quality or {}).get("processing")
    if processing:
        next_quality["processing"] = processing
    return next_quality


@router.post("/meetings", response_model=MeetingOut)
def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["tags"] = normalize_tags(data.get("tags"))
    meeting = Meeting(**data)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.get("/meetings", response_model=list[MeetingOut])
def list_meetings(
    tag: str | None = None,
    status: str | None = None,
    source_type: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Meeting)
    if tag:
        normalized = normalize_tags([tag])
        if normalized:
            query = query.filter(cast(Meeting.tags, String).ilike(f"%{normalized[0]}%"))
    if status:
        query = query.filter(cast(Meeting.status, String) == status)
    if source_type:
        query = query.filter(cast(Meeting.source_type, String) == source_type)
    query_text = q.strip() if q else ""
    if query_text:
        pattern = f"%{query_text}%"
        query = query.filter(
            or_(
                Meeting.title.ilike(pattern),
                Meeting.transcript_text.ilike(pattern),
                cast(Meeting.tags, String).ilike(pattern),
            )
        )
    return query.order_by(Meeting.id.desc()).all()


@router.get("/tags", response_model=list[str])
def list_tags(db: Session = Depends(get_db)):
    tags: set[str] = set()
    for row_tags in db.query(Meeting.tags).all():
        for tag in normalize_tags(row_tags[0]):
            tags.add(tag)
    return sorted(tags)


@router.get("/meeting-views", response_model=list[MeetingSavedViewOut])
def list_meeting_saved_views(
    workspace_id: int = 1, db: Session = Depends(get_db)
):
    views = (
        db.query(MeetingSavedView)
        .filter(MeetingSavedView.workspace_id == workspace_id)
        .order_by(MeetingSavedView.created_at.desc(), MeetingSavedView.id.desc())
        .all()
    )
    return [saved_view_out(view) for view in views]


@router.post("/meeting-views", response_model=MeetingSavedViewOut)
def create_meeting_saved_view(
    payload: MeetingSavedViewCreate, db: Session = Depends(get_db)
):
    name = " ".join(payload.name.strip().split())
    if not name:
        raise HTTPException(400, "Saved view name is required")

    filters = normalize_meeting_filters(payload.filters)
    if not filters:
        raise HTTPException(400, "Choose at least one filter before saving a view")

    view = MeetingSavedView(
        workspace_id=payload.workspace_id,
        name=name[:120],
        filters_json=filters,
    )
    db.add(view)
    db.commit()
    db.refresh(view)
    return saved_view_out(view)


@router.delete("/meeting-views/{view_id}")
def delete_meeting_saved_view(view_id: int, db: Session = Depends(get_db)):
    view = db.get(MeetingSavedView, view_id)
    if not view:
        raise HTTPException(404)
    db.delete(view)
    db.commit()
    return {"ok": True}


@router.get("/calendar/accounts", response_model=list[CalendarAccountOut])
def list_calendar_accounts(
    workspace_id: int = 1,
    include_disconnected: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(CalendarAccount).filter(CalendarAccount.workspace_id == workspace_id)
    if not include_disconnected:
        query = query.filter(CalendarAccount.status != "disconnected")
    accounts = query.order_by(CalendarAccount.created_at.desc(), CalendarAccount.id.desc()).all()
    return [calendar_account_out(account) for account in accounts]


@router.get("/calendar/providers", response_model=list[CalendarProviderStatusOut])
def list_calendar_providers():
    return list_calendar_provider_statuses()


@router.get("/calendar/oauth/{provider}/start", response_model=CalendarOAuthStartOut)
def start_calendar_oauth(provider: str, workspace_id: int = 1):
    try:
        return build_calendar_authorization_url(provider, workspace_id=workspace_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/calendar/oauth/{provider}/callback")
async def calendar_oauth_callback(
    provider: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error:
        raise HTTPException(400, f"{provider} OAuth failed: {error}")
    if not code:
        raise HTTPException(400, "OAuth callback missing authorization code")

    workspace_id = 1
    for part in (state or "").split("&"):
        key, _, value = part.partition("=")
        if key == "workspace_id" and value.isdigit():
            workspace_id = int(value)

    try:
        token_data = await exchange_calendar_oauth_code(provider, code=code)
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(502, "OAuth provider did not return an access token")
        profile = await fetch_calendar_account_profile(provider, access_token)
    except TokenEncryptionError as e:
        raise HTTPException(500, str(e))
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            e.response.status_code,
            f"{provider} token exchange failed: {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(502, f"{provider} token exchange request failed: {e}")
    except ValueError as e:
        raise HTTPException(400, str(e))

    normalized_provider = "microsoft" if provider == "outlook" else provider
    account = (
        db.query(CalendarAccount)
        .filter(CalendarAccount.workspace_id == workspace_id)
        .filter(CalendarAccount.provider == normalized_provider)
        .filter(CalendarAccount.account_email == profile["account_email"])
        .first()
    )
    if account:
        account.status = "connected"
        account.display_name = profile.get("display_name") or account.display_name
        account.provider_metadata_json = profile.get("raw") or {}
    else:
        account = CalendarAccount(
            workspace_id=workspace_id,
            provider=normalized_provider,
            account_email=profile["account_email"],
            display_name=profile.get("display_name"),
            status="connected",
            provider_metadata_json=profile.get("raw") or {},
        )
        db.add(account)
        db.flush()

    existing_token = (
        db.query(CalendarAccountToken)
        .filter(CalendarAccountToken.calendar_account_id == account.id)
        .first()
    )
    try:
        token = build_calendar_account_token(
            token_data,
            existing_encrypted_refresh_token=(
                existing_token.encrypted_refresh_token if existing_token else None
            ),
        )
    except TokenEncryptionError as e:
        raise HTTPException(500, str(e))

    account.scopes_json = token.scopes_json
    if existing_token:
        existing_token.token_type = token.token_type
        existing_token.encrypted_access_token = token.encrypted_access_token
        existing_token.encrypted_refresh_token = token.encrypted_refresh_token
        existing_token.expires_at = token.expires_at
        existing_token.scopes_json = token.scopes_json
        existing_token.provider_token_json = token.provider_token_json
    else:
        token.calendar_account_id = account.id
        db.add(token)

    db.commit()
    db.refresh(account)
    return {
        "provider": provider,
        "state": state,
        "status": "connected",
        "account_id": account.id,
        "account_email": account.account_email,
        "message": "Calendar OAuth token exchange completed and tokens were stored encrypted.",
    }


@router.post("/calendar/accounts", response_model=CalendarAccountOut)
def create_calendar_account(
    payload: CalendarAccountCreate,
    db: Session = Depends(get_db),
):
    account = CalendarAccount(
        workspace_id=payload.workspace_id,
        provider=payload.provider,
        account_email=payload.account_email,
        display_name=payload.display_name.strip()[:255] if payload.display_name else None,
        status="connected",
        scopes_json=payload.scopes,
        provider_metadata_json=payload.provider_metadata,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return calendar_account_out(account)


@router.post("/calendar/accounts/{account_id}/sync", response_model=CalendarSyncResultOut)
async def sync_calendar_account_route(
    account_id: int,
    payload: CalendarSyncRequest | None = None,
    db: Session = Depends(get_db),
):
    account = db.get(CalendarAccount, account_id)
    if not account:
        raise HTTPException(404)
    sync_request = payload or CalendarSyncRequest()
    days_back = min(sync_request.days_back, 365)
    days_forward = min(sync_request.days_forward, 365)
    max_results = max(1, min(sync_request.max_results, 1000))
    max_pages = max(1, min(sync_request.max_pages, 20))
    sync_window = {
        "days_back": days_back,
        "days_forward": days_forward,
        "max_results": max_results,
        "max_pages": max_pages,
    }
    token = (
        db.query(CalendarAccountToken)
        .filter(CalendarAccountToken.calendar_account_id == account.id)
        .first()
    )
    result = sync_calendar_account(account, token)
    if result["status"] != "ready":
        if result["status"] not in {"not_configured", "not_connected"}:
            account.last_sync_at = func.now()
            db.commit()
        return result

    refreshed = False
    try:
        if calendar_access_token_needs_refresh(token):
            refreshed_token = await refresh_calendar_access_token(account.provider, token)
            apply_refreshed_calendar_token(token, refreshed_token)
            refreshed = True
            db.commit()
        normalized_events = await fetch_provider_calendar_events(
            account,
            token,
            days_back=days_back,
            days_forward=days_forward,
            limit=max_results,
            max_pages=max_pages,
        )
    except TokenEncryptionError as e:
        raise HTTPException(500, str(e))
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            try:
                refreshed_token = await refresh_calendar_access_token(account.provider, token)
                apply_refreshed_calendar_token(token, refreshed_token)
                refreshed = True
                db.commit()
                normalized_events = await fetch_provider_calendar_events(
                    account,
                    token,
                    days_back=days_back,
                    days_forward=days_forward,
                    limit=max_results,
                    max_pages=max_pages,
                )
            except TokenEncryptionError as refresh_error:
                raise HTTPException(500, str(refresh_error))
            except httpx.HTTPStatusError as refresh_error:
                raise HTTPException(
                    refresh_error.response.status_code,
                    "Calendar token refresh failed. Reconnect the calendar account. "
                    f"Provider detail: {refresh_error.response.text}",
                )
            except httpx.RequestError as refresh_error:
                raise HTTPException(
                    502,
                    f"{account.provider} calendar token refresh request failed: {refresh_error}",
                )
            except ValueError as refresh_error:
                raise HTTPException(400, str(refresh_error))
        else:
            raise HTTPException(
                e.response.status_code,
                f"{account.provider} calendar sync failed: {e.response.text}",
            )
    except httpx.RequestError as e:
        raise HTTPException(502, f"{account.provider} calendar sync request failed: {e}")
    except ValueError as e:
        raise HTTPException(400, str(e))

    imported = 0
    updated = 0
    for event_payload in normalized_events:
        _, created = upsert_calendar_event(db, account, event_payload)
        if created:
            imported += 1
        else:
            updated += 1

    account.last_sync_at = func.now()
    account.provider_metadata_json = {
        **(account.provider_metadata_json or {}),
        "last_sync_result": {
            "imported": imported,
            "updated": updated,
            "token_refreshed": refreshed,
            "events_scanned": len(normalized_events),
            "sync_window": sync_window,
        },
    }
    db.commit()
    return {
        "account_id": account.id,
        "provider": account.provider,
        "status": "synced",
        "message": f"Imported {imported} and updated {updated} calendar event(s).",
        "events_imported": imported,
        "events_updated": updated,
        "token_refreshed": refreshed,
        "events_scanned": len(normalized_events),
        "sync_window": sync_window,
    }


@router.post("/calendar/accounts/{account_id}/disconnect", response_model=CalendarAccountOut)
def disconnect_calendar_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(CalendarAccount, account_id)
    if not account:
        raise HTTPException(404)
    account.status = "disconnected"
    db.commit()
    db.refresh(account)
    return calendar_account_out(account)


@router.get("/calendar/events", response_model=list[CalendarEventOut])
def list_calendar_events(
    workspace_id: int = 1,
    calendar_account_id: int | None = None,
    provider: str | None = None,
    q: str | None = None,
    import_status: str = "all",
    has_meeting_url: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(CalendarEvent).filter(CalendarEvent.workspace_id == workspace_id)
    if calendar_account_id:
        query = query.filter(CalendarEvent.calendar_account_id == calendar_account_id)
    if provider:
        normalized_provider = provider.strip().lower()
        if normalized_provider != "all":
            query = query.join(
                CalendarAccount,
                CalendarAccount.id == CalendarEvent.calendar_account_id,
            ).filter(CalendarAccount.provider == normalized_provider)
    query_text = q.strip() if q else ""
    if query_text:
        pattern = f"%{query_text}%"
        query = query.filter(
            or_(
                CalendarEvent.title.ilike(pattern),
                CalendarEvent.organizer_email.ilike(pattern),
                CalendarEvent.location.ilike(pattern),
                CalendarEvent.description.ilike(pattern),
            )
        )
    if import_status == "imported":
        query = query.filter(CalendarEvent.imported_meeting_id.isnot(None))
    elif import_status == "not_imported":
        query = query.filter(CalendarEvent.imported_meeting_id.is_(None))
    elif import_status != "all":
        raise HTTPException(
            400,
            "import_status must be one of: all, imported, not_imported.",
        )
    if has_meeting_url is not None:
        if has_meeting_url:
            query = query.filter(CalendarEvent.meeting_url.isnot(None))
        else:
            query = query.filter(CalendarEvent.meeting_url.is_(None))
    if date_from:
        query = query.filter(CalendarEvent.starts_at >= date_from)
    if date_to:
        query = query.filter(CalendarEvent.starts_at <= date_to)

    safe_limit = max(1, min(limit, 250))
    events = (
        query.order_by(CalendarEvent.starts_at.desc(), CalendarEvent.id.desc())
        .limit(safe_limit)
        .all()
    )
    return [calendar_event_out(event) for event in events]


@router.post("/calendar/events", response_model=CalendarEventOut)
def import_calendar_event(
    payload: CalendarEventCreate,
    db: Session = Depends(get_db),
):
    account = db.get(CalendarAccount, payload.calendar_account_id)
    if not account or account.status == "disconnected":
        raise HTTPException(404, "Connected calendar account not found")

    event, _ = upsert_calendar_event(
        db,
        account,
        {
            "external_event_id": payload.external_event_id,
            "title": payload.title,
            "starts_at": payload.starts_at,
            "ends_at": payload.ends_at,
            "organizer_email": payload.organizer_email,
            "meeting_url": payload.meeting_url,
            "location": payload.location,
            "description": payload.description,
            "attendees": payload.attendees,
            "artifacts": payload.artifacts,
            "raw": payload.raw,
        },
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409,
            "Calendar event already exists for this account and external event ID.",
        )
    db.refresh(event)
    return calendar_event_out(event)


@router.post(
    "/calendar/events/create-meetings",
    response_model=CalendarBulkMeetingCreateOut,
)
def create_meetings_from_calendar_events(
    payload: CalendarBulkMeetingCreate,
    db: Session = Depends(get_db),
):
    requested_ids = list(dict.fromkeys(payload.event_ids))[:250]
    if not requested_ids:
        return CalendarBulkMeetingCreateOut(
            requested=0,
            eligible=0,
            created=0,
            events=[],
        )

    events = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.id.in_(requested_ids))
        .order_by(CalendarEvent.starts_at.desc(), CalendarEvent.id.desc())
        .all()
    )
    events_by_id = {event.id: event for event in events}
    skipped_existing = 0
    skipped_missing_link = 0
    created = 0
    changed_events: list[CalendarEvent] = []

    for event_id in requested_ids:
        event = events_by_id.get(event_id)
        if not event:
            continue
        if event.imported_meeting_id:
            if db.get(Meeting, event.imported_meeting_id):
                skipped_existing += 1
                changed_events.append(event)
                continue
            event.imported_meeting_id = None
        if payload.require_meeting_url and not event.meeting_url:
            skipped_missing_link += 1
            changed_events.append(event)
            continue
        _, did_create = create_meeting_record_from_calendar_event(
            db,
            event,
            tags=payload.tags,
        )
        created += 1 if did_create else 0
        skipped_existing += 0 if did_create else 1
        changed_events.append(event)

    db.commit()
    for event in changed_events:
        db.refresh(event)

    return CalendarBulkMeetingCreateOut(
        requested=len(requested_ids),
        eligible=len(events),
        created=created,
        skipped_existing=skipped_existing,
        skipped_missing_link=skipped_missing_link,
        skipped_missing_event=len(requested_ids) - len(events),
        events=[calendar_event_out(event) for event in changed_events],
    )


@router.post("/calendar/events/{event_id}/create-meeting", response_model=CalendarEventOut)
def create_meeting_from_calendar_event(
    event_id: int,
    payload: CalendarEventMeetingCreate | None = None,
    db: Session = Depends(get_db),
):
    event = db.get(CalendarEvent, event_id)
    if not event:
        raise HTTPException(404)
    event, _ = create_meeting_record_from_calendar_event(
        db,
        event,
        tags=payload.tags if payload else [],
    )
    db.commit()
    db.refresh(event)
    return calendar_event_out(event)


@router.get("/search", response_model=list[SearchResultOut])
def search(q: str, db: Session = Depends(get_db)):
    query = q.strip()
    if not query:
        return []

    pattern = f"%{query}%"
    results: list[SearchResultOut] = []

    meetings = (
        db.query(Meeting)
        .filter(
            or_(
                Meeting.title.ilike(pattern),
                Meeting.transcript_text.ilike(pattern),
                cast(Meeting.tags, String).ilike(pattern),
            )
        )
        .order_by(Meeting.updated_at.desc(), Meeting.id.desc())
        .limit(20)
        .all()
    )
    for meeting in meetings:
        title_match = query.lower() in meeting.title.lower()
        tag_match = any(query.lower() in tag for tag in normalize_tags(meeting.tags))
        results.append(
            SearchResultOut(
                kind="meeting",
                meeting_id=meeting.id,
                meeting_title=meeting.title,
                title=(
                    meeting.title
                    if title_match
                    else "Tag match"
                    if tag_match
                    else "Transcript match"
                ),
                excerpt=(
                    meeting.title
                    if title_match
                    else ", ".join(normalize_tags(meeting.tags))
                    if tag_match
                    else search_excerpt(meeting.transcript_text, query)
                ),
                status=meeting.status.value if hasattr(meeting.status, "value") else str(meeting.status),
            )
        )

    summaries = (
        db.query(MeetingAIOutput, Meeting.title.label("meeting_title"))
        .join(Meeting, MeetingAIOutput.meeting_id == Meeting.id)
        .filter(cast(MeetingAIOutput.summary_json, String).ilike(pattern))
        .order_by(MeetingAIOutput.updated_at.desc(), MeetingAIOutput.id.desc())
        .limit(20)
        .all()
    )
    for output, meeting_title in summaries:
        summary_text = str(output.summary_json)
        results.append(
            SearchResultOut(
                kind="summary",
                meeting_id=output.meeting_id,
                meeting_title=meeting_title,
                title="AI notes match",
                excerpt=search_excerpt(summary_text, query),
                status=None,
            )
        )

    action_items = (
        db.query(ActionItem, Meeting.title.label("meeting_title"))
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(ActionItem.archived_at.is_(None))
        .filter(
            or_(
                ActionItem.task.ilike(pattern),
                ActionItem.owner.ilike(pattern),
                ActionItem.evidence.ilike(pattern),
            )
        )
        .order_by(ActionItem.created_at.desc(), ActionItem.id.desc())
        .limit(20)
        .all()
    )
    for item, meeting_title in action_items:
        haystack = " ".join(
            value for value in [item.task, item.owner, item.evidence] if value
        )
        results.append(
            SearchResultOut(
                kind="action",
                meeting_id=item.meeting_id,
                meeting_title=meeting_title,
                title=item.task,
                excerpt=search_excerpt(haystack, query),
                status=item.status,
            )
        )

    return results[:50]


@router.get("/meetings/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404)
    return meeting


@router.get(
    "/meetings/{meeting_id}/calendar-event",
    response_model=MeetingCalendarEventOut,
)
def get_meeting_calendar_event(meeting_id: int, db: Session = Depends(get_db)):
    event = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.imported_meeting_id == meeting_id)
        .first()
    )
    if not event:
        raise HTTPException(404)
    return meeting_calendar_event_out(event)


@router.get(
    "/meetings/{meeting_id}/artifact-matches",
    response_model=list[MeetingArtifactMatchOut],
)
def get_meeting_artifact_matches(
    meeting_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404)

    has_artifact = bool(
        meeting.audio_file_path
        or meeting.video_file_path
        or (meeting.transcript_text and meeting.transcript_source != "calendar")
    )
    if not has_artifact:
        return []

    events = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.workspace_id == meeting.workspace_id)
        .filter(
            or_(
                CalendarEvent.imported_meeting_id.is_(None),
                CalendarEvent.imported_meeting_id != meeting.id,
            )
        )
        .order_by(CalendarEvent.starts_at.desc(), CalendarEvent.id.desc())
        .limit(100)
        .all()
    )
    linked_meeting_ids = [
        event.imported_meeting_id for event in events if event.imported_meeting_id
    ]
    linked_meetings = (
        {
            item.id: item
            for item in db.query(Meeting)
            .filter(Meeting.id.in_(linked_meeting_ids))
            .all()
        }
        if linked_meeting_ids
        else {}
    )

    matches: list[MeetingArtifactMatchOut] = []
    for event in events:
        score, reasons = artifact_match_score(meeting, event)
        if score < 10:
            continue
        linked_meeting = (
            linked_meetings.get(event.imported_meeting_id)
            if event.imported_meeting_id
            else None
        )
        matches.append(
            MeetingArtifactMatchOut(
                calendar_event_id=event.id,
                title=event.title,
                starts_at=event.starts_at,
                meeting_url=event.meeting_url,
                imported_meeting_id=event.imported_meeting_id,
                imported_meeting_title=linked_meeting.title if linked_meeting else None,
                score=score,
                reasons=reasons,
                action=(
                    "merge"
                    if event.imported_meeting_id and event.imported_meeting_id != meeting.id
                    else "link"
                ),
            )
        )

    safe_limit = max(1, min(limit, 10))
    return sorted(matches, key=lambda item: item.score, reverse=True)[:safe_limit]


@router.post(
    "/meetings/{meeting_id}/artifact-matches/{calendar_event_id}/attach",
    response_model=MeetingArtifactAttachOut,
)
def attach_meeting_artifact_to_calendar_event(
    meeting_id: int,
    calendar_event_id: int,
    db: Session = Depends(get_db),
):
    source = db.get(Meeting, meeting_id)
    if not source:
        raise HTTPException(404)
    event = db.get(CalendarEvent, calendar_event_id)
    if not event or event.workspace_id != source.workspace_id:
        raise HTTPException(404, "Calendar event not found for this workspace")

    copied_fields: list[str] = []
    target = source
    merged = False
    if event.imported_meeting_id:
        existing_target = db.get(Meeting, event.imported_meeting_id)
        if existing_target:
            target = existing_target
            if target.id != source.id:
                merged = True
                copied_fields = copy_artifact_fields(source, target)
        else:
            event.imported_meeting_id = None

    if not event.imported_meeting_id:
        event.imported_meeting_id = source.id
        source.meeting_date = source.meeting_date or event.starts_at
        source.tags = normalize_tags(
            (source.tags or []) + ["calendar", "matched-artifact"]
        )
        copied_fields.append("calendar_event_link")

    db.commit()
    db.refresh(source)
    db.refresh(target)
    db.refresh(event)
    return MeetingArtifactAttachOut(
        source_meeting=source,
        target_meeting=target,
        calendar_event=meeting_calendar_event_out(event),
        merged=merged,
        copied_fields=copied_fields,
    )


@router.get("/meetings/{meeting_id}/related", response_model=list[RelatedMeetingOut])
def related_meetings(
    meeting_id: int,
    limit: int = 6,
    db: Session = Depends(get_db),
):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404)

    limit = max(1, min(limit, 12))
    all_meetings = db.query(Meeting).filter(Meeting.id != meeting_id).all()
    meeting_ids = [candidate.id for candidate in all_meetings] + [meeting_id]
    outputs = {
        output.meeting_id: output
        for output in db.query(MeetingAIOutput)
        .filter(MeetingAIOutput.meeting_id.in_(meeting_ids))
        .all()
    }
    action_items_by_meeting: dict[int, list[ActionItem]] = {
        next_id: [] for next_id in meeting_ids
    }
    for item in (
        db.query(ActionItem)
        .filter(ActionItem.meeting_id.in_(meeting_ids))
        .filter(ActionItem.archived_at.is_(None))
        .all()
    ):
        action_items_by_meeting.setdefault(item.meeting_id, []).append(item)

    current_tags = set(normalize_tags(meeting.tags))
    current_terms = memory_terms(
        meeting_memory_blob(
            meeting,
            outputs.get(meeting.id),
            action_items_by_meeting.get(meeting.id, []),
        )
    )
    current_title_terms = memory_terms(meeting.title, limit=12)
    current_source = meeting_source_value(meeting)

    related: list[RelatedMeetingOut] = []
    for candidate in all_meetings:
        candidate_tags = set(normalize_tags(candidate.tags))
        candidate_blob = meeting_memory_blob(
            candidate,
            outputs.get(candidate.id),
            action_items_by_meeting.get(candidate.id, []),
        )
        candidate_terms = memory_terms(candidate_blob)
        candidate_title_terms = memory_terms(candidate.title, limit=12)

        shared_tags = sorted(current_tags & candidate_tags)
        shared_title_terms = sorted(current_title_terms & candidate_title_terms)
        shared_terms = sorted((current_terms & candidate_terms) - set(shared_title_terms))

        score = 0
        reasons: list[str] = []
        if shared_tags:
            score += min(45, len(shared_tags) * 22)
            reasons.append(f"Shared tag: {shared_tags[0]}")
        if shared_title_terms:
            score += min(24, len(shared_title_terms) * 8)
            reasons.append(f"Title overlap: {shared_title_terms[0]}")
        if shared_terms:
            score += min(36, len(shared_terms) * 3)
            reasons.append("Shared context: " + ", ".join(shared_terms[:3]))
        if score and meeting_source_value(candidate) == current_source:
            score += 3
            reasons.append(f"Same source: {current_source}")

        if score:
            related.append(
                RelatedMeetingOut(
                    meeting_id=candidate.id,
                    meeting_title=candidate.title,
                    status=meeting_status_value(candidate),
                    source_type=meeting_source_value(candidate),
                    tags=normalize_tags(candidate.tags),
                    score=score,
                    reasons=reasons[:4],
                    excerpt=related_excerpt(candidate, outputs.get(candidate.id)),
                )
            )

    return sorted(related, key=lambda item: item.score, reverse=True)[:limit]


@router.get("/transcription/status", response_model=TranscriptionProviderStatusOut)
def transcription_status():
    return get_transcription_provider_status()


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


@router.patch("/meetings/{meeting_id}/tags", response_model=MeetingOut)
def patch_meeting_tags(
    meeting_id: int, payload: MeetingTagsUpdate, db: Session = Depends(get_db)
):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404)
    meeting.tags = normalize_tags(payload.tags)
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
    summarizer = build_meeting_summarizer(llm, model)
    try:
        await process_meeting(meeting, db, summarizer, provider_name, model)
        return {"ok": True}
    except LLMProviderError as e:
        status = e.status_code or 502
        # Preserve rate limiting semantics for the frontend.
        if status == 429:
            detail = "Rate limited by OpenRouter. Try again in a bit."
            if e.retry_after_seconds:
                detail = f"{detail} Retry after about {e.retry_after_seconds} seconds."
            raise HTTPException(429, detail)
        raise HTTPException(status, e.message)
    except ValidationError as e:
        raise HTTPException(
            422,
            "AI output did not match the required meeting note structure. "
            f"Try processing again or switch models. Validation detail: {e}",
        )
    except Exception as e:
        raise HTTPException(502, f"Meeting processing failed: {e}")


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
    meeting = db.get(Meeting, meeting_id)
    if meeting:
        out.quality_json = preserve_processing_quality_metadata(
            out.quality_json,
            evaluate_summary_quality(meeting.transcript_text or "", validated),
        )
        if "action_items" in payload.model_dump(exclude_unset=True):
            sync_generated_action_items(db, meeting_id, validated)
    db.commit()
    db.refresh(out)
    return out


@router.post(
    "/meetings/{meeting_id}/ai-output/summary/regenerate",
    response_model=MeetingAIOutputOut,
)
async def regenerate_meeting_summary_section(
    meeting_id: int,
    payload: MeetingSummaryRegenerateIn,
    db: Session = Depends(get_db),
):
    section = payload.section.strip()
    if section not in REGENERATABLE_SECTIONS:
        raise HTTPException(400, f"Unsupported summary section: {section}")

    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404)
    if not meeting.transcript_text:
        raise HTTPException(400, "Transcript required to regenerate a section")

    out = db.query(MeetingAIOutput).filter_by(meeting_id=meeting_id).first()
    if not out:
        raise HTTPException(404, "Process the meeting before regenerating sections")

    try:
        current_summary = MeetingSummarySchema.model_validate(out.summary_json)
    except Exception as e:
        raise HTTPException(400, f"Stored summary is invalid: {e}")

    try:
        provider_name, model, llm = get_llm_provider()
    except ValueError as e:
        raise HTTPException(500, str(e))

    summarizer = build_meeting_summarizer(llm, model)
    meeting.status = MeetingStatus.summarizing
    meeting.processing_error = None
    db.commit()

    try:
        regenerated_value = await summarizer.regenerate_section(
            meeting.transcript_text, current_summary, section
        )
        next_summary = {**current_summary.model_dump(), section: regenerated_value}
        validated = MeetingSummarySchema.model_validate(next_summary)

        out.provider = provider_name
        out.model = model
        out.summary_json = validated.model_dump()
        out.quality_json = preserve_processing_quality_metadata(
            out.quality_json,
            evaluate_summary_quality(meeting.transcript_text or "", validated),
        )
        if section == "action_items":
            sync_generated_action_items(db, meeting_id, validated)
        meeting.status = MeetingStatus.completed
        meeting.processing_error = None
        db.commit()
        db.refresh(out)
        return out
    except LLMProviderError as e:
        meeting.status = MeetingStatus.failed
        meeting.processing_error = e.message
        db.commit()
        status = e.status_code or 502
        if status == 429:
            raise HTTPException(429, "Rate limited by OpenRouter. Try again in a bit.")
        raise HTTPException(status, e.message)
    except ValidationError as e:
        meeting.status = MeetingStatus.failed
        meeting.processing_error = (
            f"Regenerated {section} did not match the required schema."
        )
        db.commit()
        raise HTTPException(
            422,
            f"Regenerated {section} did not match the required schema: {e}",
        )
    except Exception as e:
        meeting.status = MeetingStatus.failed
        meeting.processing_error = str(e)
        db.commit()
        raise HTTPException(502, f"Regenerating {section} failed: {e}")


@router.get("/action-items", response_model=list[ActionItemOut])
def list_action_items(
    status: str | None = None,
    include_archived: bool = False,
    db: Session = Depends(get_db),
):
    query = (
        db.query(ActionItem, Meeting.title.label("meeting_title"))
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .order_by(ActionItem.created_at.desc(), ActionItem.id.desc())
    )
    if not include_archived:
        query = query.filter(ActionItem.archived_at.is_(None))
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


@router.post("/action-items/{action_item_id}/archive", response_model=ActionItemOut)
def archive_action_item(action_item_id: int, db: Session = Depends(get_db)):
    item = db.get(ActionItem, action_item_id)
    if not item:
        raise HTTPException(404)

    meeting = db.get(Meeting, item.meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")

    item.archived_at = func.now()
    db.commit()
    db.refresh(item)
    return action_item_out(item, meeting.title)


@router.post("/action-items/{action_item_id}/restore", response_model=ActionItemOut)
def restore_action_item(action_item_id: int, db: Session = Depends(get_db)):
    item = db.get(ActionItem, action_item_id)
    if not item:
        raise HTTPException(404)

    meeting = db.get(Meeting, item.meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")

    item.archived_at = None
    db.commit()
    db.refresh(item)
    return action_item_out(item, meeting.title)


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
