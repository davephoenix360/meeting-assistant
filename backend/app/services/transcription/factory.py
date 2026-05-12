from app.core.config import settings
from app.services.transcription.base import TranscriptionProvider
from app.services.transcription.local_whisper import LocalWhisperTranscriptionProvider
from app.services.transcription.placeholder import PlaceholderTranscriptionProvider


def get_transcription_provider() -> tuple[str, TranscriptionProvider]:
    provider_name = settings.transcription_provider.lower().strip()

    if provider_name == "placeholder":
        return provider_name, PlaceholderTranscriptionProvider()

    if provider_name == "local_whisper":
        return (
            provider_name,
            LocalWhisperTranscriptionProvider(
                model_size=settings.local_whisper_model,
                device=settings.local_whisper_device,
                compute_type=settings.local_whisper_compute_type,
            ),
        )

    raise ValueError(f"Unsupported transcription provider: {settings.transcription_provider}")
