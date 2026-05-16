import re
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.models.models import CalendarAccount, CalendarAccountToken, CalendarEvent
from app.services.artifacts.providers import (
    GOOGLE_MEET_ARTIFACT_SCOPES,
    _missing_scopes,
)
from app.services.calendar.token_crypto import TokenEncryptionError, decrypt_token


GOOGLE_MEET_DOCS_URL = "https://developers.google.com/workspace/meet/api/guides/artifacts"


def extract_google_meet_code(meeting_url: str | None) -> str | None:
    if not meeting_url:
        return None
    match = re.search(r"meet\.google\.com/([a-z]{3}-[a-z]{4}-[a-z]{3})", meeting_url)
    return match.group(1) if match else None


def granted_google_scopes(
    account: CalendarAccount,
    token: CalendarAccountToken | None,
) -> list[str]:
    scopes = list(account.scopes_json or [])
    scopes.extend(token.scopes_json or [] if token else [])
    return sorted({scope for scope in scopes if str(scope).strip()})


async def google_meet_api_get(
    access_token: str,
    url: str,
    *,
    params: dict[str, str] | None = None,
) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()


def summarize_transcript(transcript: dict) -> dict:
    destination = transcript.get("docsDestination") or {}
    return {
        "artifact_type": "transcript",
        "resource_name": transcript.get("name"),
        "state": transcript.get("state"),
        "start_time": transcript.get("startTime"),
        "end_time": transcript.get("endTime"),
        "destination_url": destination.get("document"),
        "raw": transcript,
    }


def summarize_recording(recording: dict) -> dict:
    destination = recording.get("driveDestination") or {}
    return {
        "artifact_type": "recording",
        "resource_name": recording.get("name"),
        "state": recording.get("state"),
        "start_time": recording.get("startTime"),
        "end_time": recording.get("endTime"),
        "destination_url": destination.get("file"),
        "raw": recording,
    }


def _empty_probe(status: str, message: str, *, meeting_code: str | None = None) -> dict:
    return {
        "provider": "google_meet",
        "label": "Google Meet artifact probe",
        "status": status,
        "message": message,
        "meeting_code": meeting_code,
        "conference_record": None,
        "counts": {},
        "missing_scopes": [],
        "artifacts": [],
        "docs_url": GOOGLE_MEET_DOCS_URL,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


async def probe_google_meet_artifacts(
    db: Session,
    event: CalendarEvent,
) -> dict:
    account = db.get(CalendarAccount, event.calendar_account_id)
    if not account or account.status == "disconnected" or account.provider != "google":
        return _empty_probe(
            "not_connected",
            "Connect a Google Calendar account for this event before probing Meet artifacts.",
        )

    meeting_code = extract_google_meet_code(event.meeting_url)
    if not meeting_code:
        return _empty_probe(
            "no_meet_link",
            "This linked calendar event does not expose a Google Meet meeting code.",
        )

    token = (
        db.query(CalendarAccountToken)
        .filter(CalendarAccountToken.calendar_account_id == account.id)
        .first()
    )
    if not token or not token.encrypted_access_token:
        probe = _empty_probe(
            "not_connected",
            "This Google account is present, but no OAuth access token is stored for Meet probing.",
            meeting_code=meeting_code,
        )
        probe["missing_scopes"] = GOOGLE_MEET_ARTIFACT_SCOPES
        return probe

    granted_scopes = granted_google_scopes(account, token)
    missing_scopes = _missing_scopes(GOOGLE_MEET_ARTIFACT_SCOPES, granted_scopes)
    if missing_scopes:
        probe = _empty_probe(
            "missing_scopes",
            "The linked Google account is missing the Meet artifact scope required for probing.",
            meeting_code=meeting_code,
        )
        probe["missing_scopes"] = missing_scopes
        return probe

    try:
        access_token = decrypt_token(token.encrypted_access_token)
    except TokenEncryptionError as exc:
        return _empty_probe(
            "token_error",
            str(exc),
            meeting_code=meeting_code,
        )
    if not access_token:
        return _empty_probe(
            "not_connected",
            "The linked Google account does not have a readable access token for Meet probing.",
            meeting_code=meeting_code,
        )

    try:
        conference_data = await google_meet_api_get(
            access_token,
            "https://meet.googleapis.com/v2/conferenceRecords",
            params={"filter": f'space.meeting_code = "{meeting_code}"', "pageSize": "1"},
        )
        conference_records = conference_data.get("conferenceRecords") or []
        if not conference_records:
            return _empty_probe(
                "not_found",
                "No Google Meet conference record was found for this meeting code.",
                meeting_code=meeting_code,
            )

        conference_record = conference_records[0]
        conference_name = str(conference_record.get("name") or "")
        transcript_data = await google_meet_api_get(
            access_token,
            f"https://meet.googleapis.com/v2/{conference_name}/transcripts",
            params={"pageSize": "20"},
        )
        recording_data = await google_meet_api_get(
            access_token,
            f"https://meet.googleapis.com/v2/{conference_name}/recordings",
            params={"pageSize": "20"},
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status in {401, 403}:
            probe = _empty_probe(
                "access_denied",
                "Google Meet denied this probe. Confirm the API is enabled and the OAuth grant includes Meet artifact scopes.",
                meeting_code=meeting_code,
            )
            probe["missing_scopes"] = GOOGLE_MEET_ARTIFACT_SCOPES
            return probe
        return _empty_probe(
            "provider_error",
            f"Google Meet probe failed: {exc.response.text}",
            meeting_code=meeting_code,
        )
    except httpx.RequestError as exc:
        return _empty_probe(
            "provider_error",
            f"Google Meet probe request failed: {exc}",
            meeting_code=meeting_code,
        )

    transcripts = [summarize_transcript(item) for item in transcript_data.get("transcripts") or []]
    recordings = [summarize_recording(item) for item in recording_data.get("recordings") or []]
    artifacts = [*transcripts, *recordings]

    return {
        "provider": "google_meet",
        "label": "Google Meet artifact probe",
        "status": "available" if artifacts else "empty",
        "message": (
            "Meet artifacts are available for this conference."
            if artifacts
            else "The conference record exists, but no transcripts or recordings are available yet."
        ),
        "meeting_code": meeting_code,
        "conference_record": conference_name,
        "counts": {
            "conference_records": len(conference_records),
            "transcripts": len(transcripts),
            "recordings": len(recordings),
        },
        "missing_scopes": [],
        "artifacts": artifacts,
        "docs_url": GOOGLE_MEET_DOCS_URL,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
