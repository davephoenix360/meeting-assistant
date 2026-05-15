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
