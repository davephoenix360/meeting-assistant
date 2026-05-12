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
- Background jobs use a simple async task runner for MVP; Redis queue integration is scaffolded with TODO markers.
- See `docs/04_MEETING_PLATFORM_ROADMAP.md` for Zoom/Meet/Teams roadmap constraints.
