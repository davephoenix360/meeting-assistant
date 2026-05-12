from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./meeting_assistant.db"
    redis_url: str = "redis://localhost:6379/0"
    openrouter_api_key: str | None = None
    openrouter_default_model: str = "openai/gpt-4.1-mini"
    upload_dir: str = "./storage/uploads"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


settings = Settings()
