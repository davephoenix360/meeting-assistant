# AI Meeting Assistant Product Plan

This is the living project planner. Update it after each completed work slice so the repo remains the source of truth for product direction, completed capabilities, and next steps.

## Product Goal

Build an AI-first meeting assistant in the same product category as Otter.ai, Fathom, Fireflies, and similar tools. The product should become useful before live meeting bots are attempted.

The long-term app should support:

- pasted transcript ingestion
- audio/video upload and transcription
- structured AI meeting notes
- key points, action items, decisions, deliverables, risks/blockers, and open questions
- follow-up email generation
- meeting library and searchable meeting memory
- cross-meeting action item management
- calendar connections
- artifact imports from Zoom, Google Meet, and Microsoft Teams where APIs and permissions allow
- live meeting bot/capture only after the core product is stable

## Core Build Principle

Build in this order:

1. Make transcript-first meeting intelligence excellent.
2. Add audio/video transcription.
3. Add search, action item management, and editing.
4. Add calendar and post-meeting artifact integrations.
5. Add platform-specific imports.
6. Add live meeting bot/capture only when the product is already useful without it.

Do not make the architecture dependent on one meeting platform or one AI provider.

## Architecture Guardrails

- Keep LLM access behind provider abstractions.
- Do not hardcode OpenRouter in route handlers.
- Store provider and model metadata for every AI output.
- Use structured JSON output where supported.
- Validate model output with Pydantic before persisting.
- For long transcripts, prefer a sequential Refine strategy with overlap and entity/action tracking for narrative cohesion. Use Map-Reduce only for very large or batch workflows where latency matters more than continuity.
- Keep meeting-source integrations behind source-specific service boundaries.
- Prefer transcript-first and artifact-first workflows before live capture.
- Keep MVP background processing simple, but leave room for a queue later.

## Current Baseline

- Next.js frontend with custom CSS app UI.
- FastAPI backend with SQLAlchemy models and Alembic migration.
- Transcript-first flow works:
  - create meeting
  - paste transcript
  - process with AI
  - save structured AI output
  - save action items
  - view summary and action items
  - export Markdown
- Meeting detail supports editing core generated summary sections before export.
- Meeting detail supports regenerating individual AI-generated sections without reprocessing the whole meeting.
- Meeting detail keeps long generated action-item lists inside a scrollable panel.
- Long transcripts are processed with sequential Refine chunking, overlap, and entity/action tracking before final structured note generation.
- Meetings support user-managed tags for library filtering and search.
- Meeting library supports reusable saved filter views.
- Meeting detail recalls related meetings from tags, summaries, transcripts, and action items.
- New meeting flow supports audio/video upload intake against the backend upload endpoint.
- Uploaded recordings can be transcribed through the active provider, with placeholder mode clearly marked.
- Local Whisper transcription provider is scaffolded behind the transcription provider abstraction for free, local speech-to-text.
- The frontend can show active transcription provider status before upload and on settings/detail screens.
- Calendar accounts and imported calendar events have provider-neutral backend models and a workspace UI.
- Calendar integration has provider status, OAuth URL, callback token exchange, encrypted token storage, and Google/Microsoft event sync.
- Calendar OAuth start routes redirect browser users to providers and support JSON debugging with `as_json=true`.
- Calendar provider sync refreshes expired or rejected access tokens with stored refresh tokens.
- Connected OAuth calendars auto-sync while the calendar page is open, with advanced sync controls hidden until needed.
- The backend runs an in-process background sync loop for connected OAuth calendars, configurable by environment variables.
- Calendar accounts expose last sync status/result/error details in the API and calendar UI.
- Provider-specific artifact permission requirements are documented for Google Meet, Microsoft Teams, and Zoom before implementation.
- Imported calendar events can create linked meeting records with calendar context attached.
- Meeting detail surfaces linked calendar event metadata, attendees, meeting URLs, and artifacts.
- Calendar events can be filtered by account, provider, date, import state, meeting-link state, and search text; repeated imports update existing events.
- Calendar sync supports configurable date windows, max result counts, provider pagination, and recurring occurrence expansion.
- Calendar event automation can bulk-create meeting records from the currently shown event set with duplicate and meeting-link safeguards.
- Uploaded recordings and pasted transcripts can surface likely calendar-event matches and attach or merge artifacts into calendar-created meetings.
- Transcript provenance metadata is persisted and displayed for pasted and transcribed meetings.
- Workspace search spans meetings, transcripts, AI summaries, and action items.
- OpenRouter provider implementation exists.
- LLM provider resolution is moving toward a factory-based abstraction.
- Cross-meeting action item workspace supports manual creation, status/owner/due filters, sorting, overdue indicators, completion toggles, inline edits, and archiving.
- AI processing persists failure context and deterministic summary quality checks for review.

## Phase Checklist

### Phase 1: Transcript-First Intelligence

- [x] Create meeting records.
- [x] Paste and persist transcript text.
- [x] Generate structured meeting summaries.
- [x] Persist provider/model metadata for AI outputs.
- [x] Display executive summary, key points, decisions, action items, deliverables, risks, open questions, and follow-up email.
- [x] Export Markdown.
- [x] Prevent duplicate AI outputs/action items when reprocessing a meeting.
- [x] Edit generated notes before export.
- [x] Add summary quality checks and better error recovery.
- [x] Regenerate individual sections.
- [x] Add long-transcript Refine processing with overlap and entity/action tracking.

### Phase 2: Action Item Workspace

- [x] Persist action items extracted from summaries.
- [x] List action items across meetings.
- [x] Filter open, done, and all action items.
- [x] Mark action items open/done.
- [x] Edit task, owner, due date, priority, and evidence from the action workspace.
- [x] Add assignee/owner filters.
- [x] Add due-date sorting and overdue indicators.
- [x] Add manual action item creation.
- [x] Add action item archiving and restore.

### Phase 3: Meeting Library And Memory

- [x] Meeting library page.
- [x] Search meetings by title, transcript, summary, and action text.
- [x] Add meeting tags.
- [x] Add saved views or filters.
- [x] Add related meetings / memory recall.

### Phase 4: Audio/Video Transcription

- [x] Upload endpoint scaffold.
- [x] Upload UI.
- [x] Local placeholder transcription path.
- [x] Real transcription provider abstraction.
- [x] Persist transcript provenance and confidence metadata.
- [x] Add transcription provider status endpoint and UI state.

### Phase 5: Calendar And Artifact Integrations

- [x] Calendar account model.
- [x] Manual calendar event import foundation.
- [x] Provider calendar event sync service boundaries.
- [x] OAuth URL and callback scaffolding.
- [x] OAuth token exchange and encrypted token storage.
- [x] Provider calendar event sync.
- [x] Token refresh handling for expired calendar access tokens.
- [x] Attach imported calendar events/artifacts to meetings.
- [x] Synced event filtering and duplicate-safe import handling.
- [x] Recurring event and pagination depth controls.
- [x] Calendar import automation controls.
- [x] Open-page auto-sync for connected OAuth calendars.
- [x] Simplify calendar UI by hiding advanced filters, sync depth controls, and manual import by default.
- [x] Durable-enough MVP background calendar sync loop for connected OAuth accounts.
- [x] Calendar sync status details for manual/background sync.
- [x] Post-meeting transcript/recording artifact matching.
- [ ] Post-meeting transcript/recording imports where provider APIs allow.

### Phase 6: Meeting Platform Integrations

- [ ] Zoom artifact import.
- [ ] Google Meet artifact import.
- [ ] Microsoft Teams artifact import.
- [x] Provider-specific permission documentation.

### Phase 7: Live Capture / Bots

- [ ] Bot architecture decision.
- [ ] Live capture proof of concept.
- [ ] Consent and compliance UX.
- [ ] Provider-specific live capture implementation.

## Active Work

- No active slice. Pick the next item from the recommendations below.

## Next Recommended Work

1. Add provider capability/status endpoints for artifact imports.
2. Add provider API artifact import probes for Zoom/Google/Microsoft.
3. Add saved calendar automation rules.
4. Add durable sync-history table if account-level status is not enough.
