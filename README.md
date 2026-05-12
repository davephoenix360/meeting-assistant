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
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
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
