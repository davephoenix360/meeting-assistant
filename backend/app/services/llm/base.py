from abc import ABC, abstractmethod


class LLMProviderError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: int | None = None,
        provider: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        self.provider = provider


class LLMProvider(ABC):
    @abstractmethod
    async def generate_text(self, messages, model: str, **kwargs) -> str: ...

    @abstractmethod
    async def generate_json(
        self, messages, schema: dict, model: str, **kwargs
    ) -> dict: ...
