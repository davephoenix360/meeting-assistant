from app.services.transcription.base import TranscriptionProvider, TranscriptResult
import os


class PlaceholderTranscriptionProvider(TranscriptionProvider):
    async def transcribe(self, file_path: str, language: str | None = None) -> TranscriptResult:
        # TODO: Replace with faster-whisper / Deepgram / AssemblyAI provider implementation.
        filename = os.path.basename(file_path)
        text = (
            "[Placeholder transcript]\n\n"
            f"Source recording: {filename}\n\n"
            "A recording has been uploaded and registered for this meeting. "
            "Replace this placeholder with a real transcription provider output "
            "before using the meeting for final AI notes."
        )
        return TranscriptResult(
            text=text,
            language=language,
            confidence=None,
            model="placeholder",
        )
