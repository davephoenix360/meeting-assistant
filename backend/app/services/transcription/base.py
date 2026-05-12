from abc import ABC, abstractmethod
from pydantic import BaseModel


class TranscriptResult(BaseModel):
    text: str
    language: str | None = None


class TranscriptionProvider(ABC):
    @abstractmethod
    async def transcribe(self, file_path: str, language: str | None = None) -> TranscriptResult: ...
