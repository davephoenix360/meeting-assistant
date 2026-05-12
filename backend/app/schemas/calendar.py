from datetime import datetime

from pydantic import BaseModel, Field, field_validator


SUPPORTED_CALENDAR_PROVIDERS = {
    "google",
    "microsoft",
    "outlook",
    "local",
}


def normalize_provider(value: str) -> str:
    provider = " ".join(value.strip().lower().split())
    if provider == "office365":
        provider = "microsoft"
    if provider not in SUPPORTED_CALENDAR_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_CALENDAR_PROVIDERS))
        raise ValueError(f"Unsupported calendar provider. Use one of: {supported}.")
    return provider


class CalendarAccountCreate(BaseModel):
    workspace_id: int = 1
    provider: str
    account_email: str
    display_name: str | None = None
    scopes: list[str] = Field(default_factory=list)
    provider_metadata: dict = Field(default_factory=dict)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        return normalize_provider(value)

    @field_validator("account_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email:
            raise ValueError("Calendar account email must be a valid email address.")
        return email

    @field_validator("scopes", mode="before")
    @classmethod
    def default_scopes(cls, value):
        return value or []

    @field_validator("provider_metadata", mode="before")
    @classmethod
    def default_provider_metadata(cls, value):
        return value or {}


class CalendarAccountOut(BaseModel):
    id: int
    workspace_id: int
    provider: str
    account_email: str
    display_name: str | None = None
    status: str
    scopes: list[str] = Field(default_factory=list)
    provider_metadata: dict = Field(default_factory=dict)
    connected_at: datetime
    last_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CalendarEventCreate(BaseModel):
    calendar_account_id: int
    external_event_id: str
    title: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    organizer_email: str | None = None
    meeting_url: str | None = None
    location: str | None = None
    description: str | None = None
    attendees: list[dict] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)

    @field_validator("external_event_id", "title")
    @classmethod
    def required_text(cls, value: str) -> str:
        next_value = value.strip()
        if not next_value:
            raise ValueError("Value is required.")
        return next_value

    @field_validator("attendees", "artifacts", mode="before")
    @classmethod
    def default_lists(cls, value):
        return value or []

    @field_validator("raw", mode="before")
    @classmethod
    def default_raw(cls, value):
        return value or {}


class CalendarEventOut(BaseModel):
    id: int
    workspace_id: int
    calendar_account_id: int
    external_event_id: str
    title: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    organizer_email: str | None = None
    meeting_url: str | None = None
    location: str | None = None
    description: str | None = None
    attendees: list[dict] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    imported_meeting_id: int | None = None
    raw: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
