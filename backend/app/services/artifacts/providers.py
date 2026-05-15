from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import CalendarAccount, CalendarAccountToken


GOOGLE_MEET_ARTIFACT_SCOPES = [
    "https://www.googleapis.com/auth/meetings.space.readonly",
]
GOOGLE_MEET_OPTIONAL_ARTIFACT_SCOPES = [
    "https://www.googleapis.com/auth/drive.meet.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

MICROSOFT_TEAMS_ARTIFACT_SCOPES = [
    "OnlineMeetingTranscript.Read.All",
    "OnlineMeetingRecording.Read.All",
]
MICROSOFT_TEAMS_RSC_SCOPES = [
    "OnlineMeetingTranscript.Read.Chat",
    "OnlineMeetingRecording.Read.Chat",
]

ZOOM_RECORDING_SCOPES = [
    "cloud_recording:read:recording",
    "cloud_recording:read:list_recording_files",
]
ZOOM_ADMIN_RECORDING_SCOPES = [
    "cloud_recording:read:recording:admin",
    "cloud_recording:read:list_recording_files:admin",
]


@dataclass(frozen=True)
class ArtifactProviderDefinition:
    provider: str
    label: str
    artifact_types: list[str]
    required_scopes: list[str]
    optional_scopes: list[str]
    admin_consent_required: bool
    docs_url: str
    setup_notes: list[str]


def _scope_key(value: str) -> str:
    return value.strip().lower()


def _configured(*values: str | None) -> bool:
    return all(bool((value or "").strip()) for value in values)


def _collect_calendar_scopes(
    db: Session,
    *,
    workspace_id: int,
    provider: str,
) -> tuple[bool, list[str]]:
    accounts = (
        db.query(CalendarAccount)
        .filter(CalendarAccount.workspace_id == workspace_id)
        .filter(CalendarAccount.provider == provider)
        .filter(CalendarAccount.status == "connected")
        .all()
    )
    account_ids = [account.id for account in accounts]
    scopes: list[str] = []
    for account in accounts:
        scopes.extend(account.scopes_json or [])

    if account_ids:
        tokens = (
            db.query(CalendarAccountToken)
            .filter(CalendarAccountToken.calendar_account_id.in_(account_ids))
            .all()
        )
        for token in tokens:
            scopes.extend(token.scopes_json or [])

    deduped = sorted({scope for scope in scopes if str(scope).strip()})
    return bool(accounts), deduped


def _missing_scopes(required_scopes: list[str], granted_scopes: list[str]) -> list[str]:
    granted = {_scope_key(scope) for scope in granted_scopes}
    return [scope for scope in required_scopes if _scope_key(scope) not in granted]


def _status_payload(
    definition: ArtifactProviderDefinition,
    *,
    configured: bool,
    connected: bool,
    granted_scopes: list[str],
    missing_scopes: list[str],
    not_available_message: str | None = None,
) -> dict:
    if not configured:
        status = "missing_credentials"
        message = f"{definition.label} artifact credentials are not configured."
    elif not connected:
        status = "missing_connection"
        message = not_available_message or f"Connect {definition.label} before importing artifacts."
    elif missing_scopes:
        status = "missing_scopes"
        message = (
            "Connected, but the current OAuth grant does not include artifact "
            "permissions."
        )
    else:
        status = "ready"
        message = "Artifact permissions appear ready for a provider probe."

    return {
        "provider": definition.provider,
        "label": definition.label,
        "configured": configured,
        "connected": connected,
        "status": status,
        "message": message,
        "artifact_types": definition.artifact_types,
        "required_scopes": definition.required_scopes,
        "optional_scopes": definition.optional_scopes,
        "granted_scopes": granted_scopes,
        "missing_scopes": missing_scopes,
        "admin_consent_required": definition.admin_consent_required,
        "setup_notes": definition.setup_notes,
        "docs_url": definition.docs_url,
    }


def google_meet_artifact_status(db: Session, workspace_id: int) -> dict:
    definition = ArtifactProviderDefinition(
        provider="google_meet",
        label="Google Meet artifacts",
        artifact_types=["transcripts", "recordings", "smart notes"],
        required_scopes=GOOGLE_MEET_ARTIFACT_SCOPES,
        optional_scopes=GOOGLE_MEET_OPTIONAL_ARTIFACT_SCOPES,
        admin_consent_required=False,
        docs_url="https://developers.google.com/workspace/meet/api/guides/artifacts",
        setup_notes=[
            "Enable the Google Meet REST API before probing artifacts.",
            "Drive scopes are only needed when downloading Meet-backed files.",
            "Restricted Drive scopes can require Google verification and security review.",
        ],
    )
    connected, granted_scopes = _collect_calendar_scopes(
        db,
        workspace_id=workspace_id,
        provider="google",
    )
    return _status_payload(
        definition,
        configured=_configured(
            settings.google_calendar_client_id,
            settings.google_calendar_client_secret,
        ),
        connected=connected,
        granted_scopes=granted_scopes,
        missing_scopes=_missing_scopes(definition.required_scopes, granted_scopes),
    )


def microsoft_teams_artifact_status(db: Session, workspace_id: int) -> dict:
    definition = ArtifactProviderDefinition(
        provider="microsoft_teams",
        label="Microsoft Teams artifacts",
        artifact_types=["transcripts", "recordings"],
        required_scopes=MICROSOFT_TEAMS_ARTIFACT_SCOPES,
        optional_scopes=MICROSOFT_TEAMS_RSC_SCOPES,
        admin_consent_required=True,
        docs_url="https://learn.microsoft.com/en-us/microsoftteams/platform/graph-api/meeting-transcripts/overview-transcripts",
        setup_notes=[
            "Broad transcript and recording permissions usually require admin consent.",
            "Organization-wide application access can require an application access policy.",
            "Teams meeting transcript and recording APIs can be metered.",
        ],
    )
    connected, granted_scopes = _collect_calendar_scopes(
        db,
        workspace_id=workspace_id,
        provider="microsoft",
    )
    return _status_payload(
        definition,
        configured=_configured(
            settings.microsoft_calendar_client_id,
            settings.microsoft_calendar_client_secret,
        ),
        connected=connected,
        granted_scopes=granted_scopes,
        missing_scopes=_missing_scopes(definition.required_scopes, granted_scopes),
    )


def zoom_artifact_status() -> dict:
    definition = ArtifactProviderDefinition(
        provider="zoom",
        label="Zoom cloud artifacts",
        artifact_types=["cloud recordings", "audio transcripts", "chat files"],
        required_scopes=ZOOM_RECORDING_SCOPES,
        optional_scopes=ZOOM_ADMIN_RECORDING_SCOPES,
        admin_consent_required=False,
        docs_url="https://developers.zoom.us/docs/api/webhooks/",
        setup_notes=[
            "Zoom artifact import will use its own provider connection, separate from calendar OAuth.",
            "Cloud recording and audio transcription must be enabled in Zoom.",
            "Some Zoom recording scopes are only available for specific app types or account levels.",
        ],
    )
    configured = _configured(settings.zoom_client_id, settings.zoom_client_secret)
    connected = configured and _configured(settings.zoom_account_id)
    return _status_payload(
        definition,
        configured=configured,
        connected=connected,
        granted_scopes=definition.required_scopes if connected else [],
        missing_scopes=[] if connected else definition.required_scopes,
        not_available_message=(
            "Zoom credentials are configured, but Zoom artifact OAuth/storage is not implemented yet."
        ),
    )


def list_artifact_provider_statuses(db: Session, *, workspace_id: int = 1) -> list[dict]:
    return [
        google_meet_artifact_status(db, workspace_id),
        microsoft_teams_artifact_status(db, workspace_id),
        zoom_artifact_status(),
    ]
