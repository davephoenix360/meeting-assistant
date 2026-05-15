from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.models import CalendarAccount, CalendarAccountToken


def add_calendar_account(
    db: Session,
    *,
    provider: str,
    scopes: list[str],
    token_scopes: list[str] | None = None,
) -> CalendarAccount:
    account = CalendarAccount(
        workspace_id=1,
        provider=provider,
        account_email=f"{provider}@example.com",
        display_name=f"{provider.title()} Test",
        status="connected",
        scopes_json=scopes,
        provider_metadata_json={"source": "test"},
    )
    db.add(account)
    db.flush()
    db.add(
        CalendarAccountToken(
            calendar_account_id=account.id,
            token_type="Bearer",
            scopes_json=token_scopes if token_scopes is not None else scopes,
        )
    )
    db.commit()
    db.refresh(account)
    return account


def provider_by_id(items: list[dict], provider: str) -> dict:
    return next(item for item in items if item["provider"] == provider)


def test_artifact_status_reports_missing_google_meet_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    add_calendar_account(
        db_session,
        provider="google",
        scopes=["openid", "https://www.googleapis.com/auth/calendar.events.readonly"],
    )

    response = client.get("/api/artifacts/providers/status?workspace_id=1")

    assert response.status_code == 200
    google = provider_by_id(response.json(), "google_meet")
    assert google["configured"] is True
    assert google["connected"] is True
    assert google["status"] == "missing_scopes"
    assert "https://www.googleapis.com/auth/meetings.space.readonly" in google["missing_scopes"]


def test_artifact_status_reports_ready_when_google_meet_scope_is_granted(
    client: TestClient,
    db_session: Session,
) -> None:
    add_calendar_account(
        db_session,
        provider="google",
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/calendar.events.readonly",
            "https://www.googleapis.com/auth/meetings.space.readonly",
        ],
    )

    response = client.get("/api/artifacts/providers/status?workspace_id=1")

    assert response.status_code == 200
    google = provider_by_id(response.json(), "google_meet")
    assert google["status"] == "ready"
    assert google["missing_scopes"] == []


def test_artifact_status_reports_zoom_credentials_missing(client: TestClient) -> None:
    response = client.get("/api/artifacts/providers/status?workspace_id=1")

    assert response.status_code == 200
    zoom = provider_by_id(response.json(), "zoom")
    assert zoom["configured"] is False
    assert zoom["status"] == "missing_credentials"
