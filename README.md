# Meeting Assistant MVP

Upload-first AI meeting assistant MVP with FastAPI backend and Next.js frontend.

## Vertical slice implemented

1. Create meeting
2. Paste transcript
3. Trigger processing
4. Summarize via provider abstraction (OpenRouter implementation)
5. Save structured AI output + action items
6. View notes and action items
7. Export Markdown

## Backend setup

```bash
cd backend
python -m venv .venv
# macOS/Linux:
#   source .venv/bin/activate
# Windows PowerShell:
#   .venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Ensure `.env` is configured before running migrations.
# - If `DATABASE_URL` points to Postgres, start Postgres locally first.
# - For a zero-dependency local setup, set `DATABASE_URL=sqlite:///./meeting_assistant.db`.
python -m alembic upgrade head
uvicorn app.main:app --reload
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

## Notes

- OpenRouter API key can be supplied with `OPENROUTER_API_KEY`.
- Long transcript processing switches to sequential Refine mode after `SUMMARIZATION_REFINE_THRESHOLD_CHARS` characters. Chunk and overlap sizes can be tuned with `SUMMARIZATION_REFINE_CHUNK_CHARS` and `SUMMARIZATION_REFINE_OVERLAP_CHARS`.
- Audio/video uploads use `TRANSCRIPTION_PROVIDER`.
  - `placeholder` saves the file and creates placeholder transcript text.
  - `local_whisper` runs local speech-to-text with `faster-whisper`; install the optional package before enabling it.
  - Tune local transcription with `LOCAL_WHISPER_MODEL`, `LOCAL_WHISPER_DEVICE`, and `LOCAL_WHISPER_COMPUTE_TYPE`.
  - Check the active provider with `GET /api/transcription/status`.
- Calendar accounts and events can be managed from `/calendar`. Google/Microsoft OAuth start URLs redirect to the provider once credentials are configured; see `docs/05_CALENDAR_INTEGRATION_NOTES.md`.
- Connected OAuth calendars sync in the background with `CALENDAR_BACKGROUND_SYNC_INTERVAL_SECONDS` and related `CALENDAR_BACKGROUND_SYNC_*` settings.
- Set `TOKEN_ENCRYPTION_KEY` before completing calendar OAuth; callbacks will reject token storage if the key is missing.
- Background jobs use a simple async task runner for MVP; Redis queue integration is scaffolded with TODO markers.
- See `docs/04_MEETING_PLATFORM_ROADMAP.md` for Zoom/Meet/Teams roadmap constraints.
