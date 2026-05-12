from abc import ABC, abstractmethod
from pydantic import BaseModel


class TranscriptResult(BaseModel):
    text: str
    language: str | None = None
    confidence: float | None = None
    model: str | None = None


class TranscriptionProviderError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        provider: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.provider = provider


class TranscriptionProvider(ABC):
    @abstractmethod
    async def transcribe(self, file_path: str, language: str | None = None) -> TranscriptResult: ...
