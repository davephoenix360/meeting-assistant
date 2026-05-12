from app.core.config import settings
from app.services.transcription.base import TranscriptionProvider
from app.services.transcription.placeholder import PlaceholderTranscriptionProvider


def get_transcription_provider() -> tuple[str, TranscriptionProvider]:
    provider_name = settings.transcription_provider.lower().strip()

    if provider_name == "placeholder":
        return provider_name, PlaceholderTranscriptionProvider()

    raise ValueError(f"Unsupported transcription provider: {settings.transcription_provider}")
