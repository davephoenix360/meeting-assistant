from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.models.models import CalendarAccount, CalendarAccountToken
from app.services.calendar.token_crypto import encrypt_token


GOOGLE_CALENDAR_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/calendar.events.readonly",
]

MICROSOFT_CALENDAR_SCOPES = [
    "openid",
    "email",
    "profile",
    "offline_access",
    "Calendars.Read",
]


@dataclass(frozen=True)
class CalendarProviderConfig:
    provider: str
    label: str
    auth_url: str
    token_url: str
    events_url: str
    client_id: str | None
    client_secret: str | None
    scopes: list[str]

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    @property
    def redirect_uri(self) -> str:
        base_url = settings.backend_public_url.rstrip("/")
        return f"{base_url}/api/calendar/oauth/{self.provider}/callback"


def calendar_provider_config(provider: str) -> CalendarProviderConfig:
    normalized = provider.lower().strip()
    if normalized == "outlook":
        normalized = "microsoft"

    if normalized == "google":
        return CalendarProviderConfig(
            provider="google",
            label="Google Calendar",
            auth_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            events_url="https://www.googleapis.com/calendar/v3/calendars/primary/events",
            client_id=settings.google_calendar_client_id,
            client_secret=settings.google_calendar_client_secret,
            scopes=GOOGLE_CALENDAR_SCOPES,
        )

    if normalized == "microsoft":
        tenant = settings.microsoft_calendar_tenant.strip() or "common"
        return CalendarProviderConfig(
            provider="microsoft",
            label="Microsoft Graph Calendar",
            auth_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            token_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            events_url="https://graph.microsoft.com/v1.0/me/calendar/events",
            client_id=settings.microsoft_calendar_client_id,
            client_secret=settings.microsoft_calendar_client_secret,
            scopes=MICROSOFT_CALENDAR_SCOPES,
        )

    raise ValueError(f"Unsupported calendar OAuth provider: {provider}")


def calendar_provider_status(provider: str) -> dict:
    config = calendar_provider_config(provider)
    return {
        "provider": config.provider,
        "label": config.label,
        "configured": config.configured,
        "client_id_configured": bool(config.client_id),
        "client_secret_configured": bool(config.client_secret),
        "redirect_uri": config.redirect_uri,
        "scopes": config.scopes,
        "auth_url": config.auth_url,
        "events_url": config.events_url,
    }


def list_calendar_provider_statuses() -> list[dict]:
    return [
        calendar_provider_status("google"),
        calendar_provider_status("microsoft"),
    ]


def build_calendar_authorization_url(provider: str, *, workspace_id: int = 1) -> dict:
    config = calendar_provider_config(provider)
    if not config.client_id:
        raise ValueError(
            f"{config.label} client ID is missing. Configure the provider before OAuth."
        )

    state = f"workspace_id={workspace_id}&provider={config.provider}"
    params = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "scope": " ".join(config.scopes),
        "state": state,
    }
    if config.provider == "google":
        params["access_type"] = "offline"
        params["prompt"] = "consent"
    elif config.provider == "microsoft":
        params["response_mode"] = "query"

    return {
        "provider": config.provider,
        "configured": config.configured,
        "authorization_url": f"{config.auth_url}?{urlencode(params)}",
        "redirect_uri": config.redirect_uri,
        "scopes": config.scopes,
        "state": state,
    }


async def exchange_calendar_oauth_code(
    provider: str,
    *,
    code: str,
) -> dict:
    config = calendar_provider_config(provider)
    if not config.configured:
        raise ValueError(f"{config.label} OAuth credentials are not configured.")

    payload = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "code": code,
        "redirect_uri": config.redirect_uri,
        "grant_type": "authorization_code",
    }
    if config.provider == "google":
        payload["access_type"] = "offline"
    elif config.provider == "microsoft":
        payload["scope"] = " ".join(config.scopes)

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(config.token_url, data=payload)
        response.raise_for_status()
        return response.json()


async def fetch_calendar_account_profile(provider: str, access_token: str) -> dict:
    normalized = "microsoft" if provider == "outlook" else provider
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=30) as client:
        if normalized == "google":
            response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers=headers,
            )
        elif normalized == "microsoft":
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers,
            )
        else:
            raise ValueError(f"Unsupported calendar profile provider: {provider}")
        response.raise_for_status()
        data = response.json()

    if normalized == "google":
        email = data.get("email")
        display_name = data.get("name")
    else:
        email = data.get("mail") or data.get("userPrincipalName")
        display_name = data.get("displayName")

    parsed_email = parseaddr(str(email or ""))[1].lower()
    if not parsed_email:
        parsed_email = f"unknown-{normalized}@calendar.local"

    return {
        "account_email": parsed_email,
        "display_name": display_name,
        "raw": data,
    }


def build_calendar_account_token(
    token_data: dict,
    *,
    existing_refresh_token: str | None = None,
    existing_encrypted_refresh_token: str | None = None,
) -> CalendarAccountToken:
    expires_in = token_data.get("expires_in")
    expires_at = None
    if isinstance(expires_in, int):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    refresh_token = token_data.get("refresh_token") or existing_refresh_token
    encrypted_refresh_token = (
        encrypt_token(refresh_token)
        if refresh_token
        else existing_encrypted_refresh_token
    )
    scopes = str(token_data.get("scope") or "").split()
    return CalendarAccountToken(
        token_type=token_data.get("token_type"),
        encrypted_access_token=encrypt_token(token_data.get("access_token")),
        encrypted_refresh_token=encrypted_refresh_token,
        expires_at=expires_at,
        scopes_json=scopes,
        provider_token_json={
            key: value
            for key, value in token_data.items()
            if key
            not in {
                "access_token",
                "refresh_token",
                "id_token",
            }
        },
    )


def sync_calendar_account(account: CalendarAccount, token: CalendarAccountToken | None = None) -> dict:
    if account.provider == "local":
        return {
            "account_id": account.id,
            "provider": account.provider,
            "status": "skipped",
            "message": "Local/manual calendar accounts do not sync with an external provider.",
            "events_imported": 0,
        }

    if token is None or not token.encrypted_refresh_token:
        return {
            "account_id": account.id,
            "provider": account.provider,
            "status": "not_connected",
            "message": "Connect this calendar with OAuth before syncing events.",
            "events_imported": 0,
        }

    provider = "microsoft" if account.provider == "outlook" else account.provider
    config = calendar_provider_config(provider)
    if not config.configured:
        return {
            "account_id": account.id,
            "provider": config.provider,
            "status": "not_configured",
            "message": f"{config.label} OAuth credentials are not configured.",
            "events_imported": 0,
        }

    return {
        "account_id": account.id,
        "provider": config.provider,
        "status": "not_connected",
        "message": (
            "Token storage is available. Provider event fetching will be added next."
        ),
        "events_imported": 0,
    }
