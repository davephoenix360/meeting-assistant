from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CalendarAccount, CalendarAccountToken, CalendarEvent, Meeting
from app.services.calendar.token_crypto import encrypt_token


def add_google_meeting_fixture(
    db: Session,
    *,
    scopes: list[str],
    meeting_url: str | None = "https://meet.google.com/abc-defg-hij",
    encrypted_access_token: str | None = None,
) -> tuple[Meeting, CalendarEvent]:
    account = CalendarAccount(
        workspace_id=1,
        provider="google",
        account_email="google@example.com",
        display_name="Google Test",
        status="connected",
        scopes_json=scopes,
        provider_metadata_json={"source": "test"},
    )
    db.add(account)
    db.flush()

    if encrypted_access_token is not None:
        db.add(
            CalendarAccountToken(
                calendar_account_id=account.id,
                token_type="Bearer",
                encrypted_access_token=encrypted_access_token,
                scopes_json=scopes,
            )
        )

    meeting = Meeting(workspace_id=1, title="Probe target")
    db.add(meeting)
    db.flush()

    event = CalendarEvent(
        workspace_id=1,
        calendar_account_id=account.id,
        external_event_id="evt-1",
        title="Calendar event",
        meeting_url=meeting_url,
        imported_meeting_id=meeting.id,
        raw_json={},
    )
    db.add(event)
    db.commit()
    db.refresh(meeting)
    db.refresh(event)
    return meeting, event


def test_google_meet_probe_reports_missing_link(
    client: TestClient,
    db_session: Session,
) -> None:
    meeting, _ = add_google_meeting_fixture(
        db_session,
        scopes=["https://www.googleapis.com/auth/meetings.space.readonly"],
        meeting_url=None,
    )

    response = client.get(f"/api/meetings/{meeting.id}/artifact-probe/google-meet")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "no_meet_link"


def test_google_meet_probe_reports_missing_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    meeting, _ = add_google_meeting_fixture(
        db_session,
        scopes=["https://www.googleapis.com/auth/calendar.events.readonly"],
        encrypted_access_token=encrypt_token("token"),
    )

    response = client.get(f"/api/meetings/{meeting.id}/artifact-probe/google-meet")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "missing_scopes"
    assert "https://www.googleapis.com/auth/meetings.space.readonly" in payload["missing_scopes"]


def test_google_meet_probe_reports_available_artifacts(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    meeting, _ = add_google_meeting_fixture(
        db_session,
        scopes=["https://www.googleapis.com/auth/meetings.space.readonly"],
        encrypted_access_token=encrypt_token("token"),
    )

    async def fake_google_meet_api_get(access_token: str, url: str, *, params=None):
        assert access_token == "token"
        if url.endswith("/conferenceRecords"):
            return {"conferenceRecords": [{"name": "conferenceRecords/123"}]}
        if url.endswith("/conferenceRecords/123/transcripts"):
            return {
                "transcripts": [
                    {
                        "name": "conferenceRecords/123/transcripts/1",
                        "state": "FILE_GENERATED",
                        "docsDestination": {"document": "https://docs.google.com/document/d/1"},
                    }
                ]
            }
        if url.endswith("/conferenceRecords/123/recordings"):
            return {
                "recordings": [
                    {
                        "name": "conferenceRecords/123/recordings/1",
                        "state": "FILE_GENERATED",
                        "driveDestination": {"file": "https://drive.google.com/file/d/1"},
                    }
                ]
            }
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(
        "app.services.artifacts.google_meet.google_meet_api_get",
        fake_google_meet_api_get,
    )

    response = client.get(f"/api/meetings/{meeting.id}/artifact-probe/google-meet")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "available"
    assert payload["counts"]["transcripts"] == 1
    assert payload["counts"]["recordings"] == 1
    assert len(payload["artifacts"]) == 2
