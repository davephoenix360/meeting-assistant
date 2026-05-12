from app.core.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.openrouter_provider import OpenRouterProvider


def get_llm_provider() -> tuple[str, str, LLMProvider]:
    provider_name = settings.llm_provider.lower().strip()

    if provider_name == "openrouter":
        return (
            provider_name,
            settings.openrouter_default_model,
            OpenRouterProvider(settings.openrouter_api_key or ""),
        )

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
