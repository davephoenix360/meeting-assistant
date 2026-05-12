import importlib.util

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


def get_transcription_provider_status() -> dict:
    provider_name = settings.transcription_provider.lower().strip()

    if provider_name == "placeholder":
        return {
            "provider": provider_name,
            "mode": "placeholder",
            "ready": True,
            "can_transcribe": False,
            "label": "Placeholder mode",
            "message": (
                "Uploads are saved, but transcription creates placeholder text. "
                "Set TRANSCRIPTION_PROVIDER=local_whisper for real local transcription."
            ),
            "model": "placeholder",
            "device": None,
            "compute_type": None,
            "package_installed": None,
        }

    if provider_name == "local_whisper":
        package_installed = importlib.util.find_spec("faster_whisper") is not None
        return {
            "provider": provider_name,
            "mode": "local",
            "ready": package_installed,
            "can_transcribe": package_installed,
            "label": (
                "Local Whisper ready"
                if package_installed
                else "Local Whisper needs setup"
            ),
            "message": (
                "Real local transcription is enabled. Longer recordings can take "
                "several minutes depending on model size and hardware."
                if package_installed
                else "TRANSCRIPTION_PROVIDER is local_whisper, but faster-whisper "
                "is not installed in the backend environment."
            ),
            "model": settings.local_whisper_model,
            "device": settings.local_whisper_device,
            "compute_type": settings.local_whisper_compute_type,
            "package_installed": package_installed,
        }

    return {
        "provider": settings.transcription_provider,
        "mode": "unsupported",
        "ready": False,
        "can_transcribe": False,
        "label": "Unsupported transcription provider",
        "message": f"Unsupported transcription provider: {settings.transcription_provider}",
        "model": None,
        "device": None,
        "compute_type": None,
        "package_installed": None,
    }
