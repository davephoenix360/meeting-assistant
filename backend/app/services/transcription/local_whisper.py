import asyncio

from app.services.transcription.base import (
    TranscriptionProvider,
    TranscriptionProviderError,
    TranscriptResult,
)


class LocalWhisperTranscriptionProvider(TranscriptionProvider):
    def __init__(
        self,
        *,
        model_size: str,
        device: str = "auto",
        compute_type: str = "default",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    async def transcribe(
        self, file_path: str, language: str | None = None
    ) -> TranscriptResult:
        return await asyncio.to_thread(self._transcribe_sync, file_path, language)

    def _transcribe_sync(
        self, file_path: str, language: str | None = None
    ) -> TranscriptResult:
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise TranscriptionProviderError(
                "Local Whisper transcription requires the optional "
                "`faster-whisper` package. Install it before setting "
                "TRANSCRIPTION_PROVIDER=local_whisper.",
                status_code=500,
                provider="local_whisper",
            ) from e

        model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )
        segments, info = model.transcribe(file_path, language=language)
        text = "\n".join(segment.text.strip() for segment in segments if segment.text)
        probability = getattr(info, "language_probability", None)
        return TranscriptResult(
            text=text.strip(),
            language=getattr(info, "language", language),
            confidence=probability,
            model=self.model_size,
        )
