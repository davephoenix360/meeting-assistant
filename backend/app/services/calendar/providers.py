from dataclasses import dataclass
from urllib.parse import urlencode

from app.core.config import settings
from app.models.models import CalendarAccount


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


def sync_calendar_account(account: CalendarAccount) -> dict:
    if account.provider == "local":
        return {
            "account_id": account.id,
            "provider": account.provider,
            "status": "skipped",
            "message": "Local/manual calendar accounts do not sync with an external provider.",
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
            "Provider sync boundary is ready, but OAuth token exchange and token "
            "storage are intentionally not connected yet."
        ),
        "events_imported": 0,
    }
