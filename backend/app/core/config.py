import json
from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./meeting_assistant.db"
    redis_url: str = "redis://localhost:6379/0"
    openrouter_api_key: str | None = None
    openrouter_default_model: str = "openai/gpt-4.1-mini"
    upload_dir: str = "./storage/uploads"
    # Keep this as a simple string so pydantic-settings doesn't require JSON
    # parsing for list types in `.env`. Accepts either CSV or JSON array.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @cached_property
    def cors_origins_list(self) -> list[str]:
        raw = (self.cors_origins or "").strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    return [str(item).strip() for item in data if str(item).strip()]
            except Exception:
                pass
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
