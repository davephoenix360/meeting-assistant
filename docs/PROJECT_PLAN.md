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
- OpenRouter provider implementation exists.
- LLM provider resolution is moving toward a factory-based abstraction.
- Cross-meeting action item workspace supports status/owner/due filters, sorting, overdue indicators, completion toggles, and inline edits.

## Phase Checklist

### Phase 1: Transcript-First Intelligence

- [x] Create meeting records.
- [x] Paste and persist transcript text.
- [x] Generate structured meeting summaries.
- [x] Persist provider/model metadata for AI outputs.
- [x] Display executive summary, key points, decisions, action items, deliverables, risks, open questions, and follow-up email.
- [x] Export Markdown.
- [x] Prevent duplicate AI outputs/action items when reprocessing a meeting.
- [ ] Edit generated notes before export.
- [ ] Regenerate individual sections.
- [ ] Add summary quality checks and better error recovery.

### Phase 2: Action Item Workspace

- [x] Persist action items extracted from summaries.
- [x] List action items across meetings.
- [x] Filter open, done, and all action items.
- [x] Mark action items open/done.
- [x] Edit task, owner, due date, priority, and evidence from the action workspace.
- [x] Add assignee/owner filters.
- [x] Add due-date sorting and overdue indicators.
- [ ] Add manual action item creation.

### Phase 3: Meeting Library And Memory

- [x] Meeting library page.
- [ ] Search meetings by title, transcript, summary, and action text.
- [ ] Add meeting tags.
- [ ] Add saved views or filters.
- [ ] Add related meetings / memory recall.

### Phase 4: Audio/Video Transcription

- [x] Upload endpoint scaffold.
- [ ] Upload UI.
- [ ] Local placeholder transcription path.
- [ ] Real transcription provider abstraction.
- [ ] Persist transcript provenance and confidence metadata.

### Phase 5: Calendar And Artifact Integrations

- [ ] Calendar account model.
- [ ] Calendar event import.
- [ ] Attach imported artifacts to meetings.
- [ ] Post-meeting transcript/recording imports where APIs allow.

### Phase 6: Meeting Platform Integrations

- [ ] Zoom artifact import.
- [ ] Google Meet artifact import.
- [ ] Microsoft Teams artifact import.
- [ ] Provider-specific permission documentation.

### Phase 7: Live Capture / Bots

- [ ] Bot architecture decision.
- [ ] Live capture proof of concept.
- [ ] Consent and compliance UX.
- [ ] Provider-specific live capture implementation.

## Active Work

- No active slice. Pick the next item from the recommendations below.

## Next Recommended Work

1. Add manual action item creation.
2. Add editable summary sections on the meeting detail page.
3. Add upload UI for audio/video and connect it to the existing upload endpoint.
4. Add search across meetings, summaries, transcripts, and action items.
