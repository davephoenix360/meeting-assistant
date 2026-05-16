from pydantic import BaseModel, Field


class ArtifactProviderStatusOut(BaseModel):
    provider: str
    label: str
    configured: bool
    connected: bool
    status: str
    message: str
    artifact_types: list[str] = Field(default_factory=list)
    required_scopes: list[str] = Field(default_factory=list)
    optional_scopes: list[str] = Field(default_factory=list)
    granted_scopes: list[str] = Field(default_factory=list)
    missing_scopes: list[str] = Field(default_factory=list)
    admin_consent_required: bool = False
    setup_notes: list[str] = Field(default_factory=list)
    docs_url: str | None = None


class ArtifactProbeItemOut(BaseModel):
    artifact_type: str
    resource_name: str | None = None
    state: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    destination_url: str | None = None
    raw: dict = Field(default_factory=dict)


class ArtifactProbeOut(BaseModel):
    provider: str
    label: str
    status: str
    message: str
    meeting_code: str | None = None
    conference_record: str | None = None
    counts: dict = Field(default_factory=dict)
    missing_scopes: list[str] = Field(default_factory=list)
    artifacts: list[ArtifactProbeItemOut] = Field(default_factory=list)
    docs_url: str | None = None
    checked_at: str | None = None
