from app.services.transcription.base import TranscriptionProvider, TranscriptResult


class PlaceholderTranscriptionProvider(TranscriptionProvider):
    async def transcribe(self, file_path: str, language: str | None = None) -> TranscriptResult:
        # TODO: Replace with faster-whisper / Deepgram / AssemblyAI provider implementation.
        raise NotImplementedError("Transcription provider not configured for MVP transcript-first flow")
