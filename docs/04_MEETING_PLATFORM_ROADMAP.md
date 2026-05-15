# Meeting Platform Roadmap (Post-MVP)

MVP remains upload/transcript-first.

## Zoom
Zoom meeting joining requires Meeting SDK and OAuth scopes. External-account joining requires additional authorization patterns (e.g., OBF/ZAK/RTMS) as of 2026.
Post-meeting artifact import should start with cloud recordings/transcripts, not live joining. See `docs/06_PROVIDER_ARTIFACT_PERMISSIONS.md`.

## Google Meet
Google Meet real-time media access is exposed via Meet Media API with Developer Preview constraints and enrollment requirements.
Post-meeting artifact import should start with Meet REST API conference artifacts and Drive-backed files. See `docs/06_PROVIDER_ARTIFACT_PERMISSIONS.md`.

## Microsoft Teams
Teams supports post-meeting transcript/recording retrieval via Microsoft Graph with proper permissions; real-time media bots are advanced and deferred.
Post-meeting artifact import requires Graph recording/transcript permissions and often admin consent. See `docs/06_PROVIDER_ARTIFACT_PERMISSIONS.md`.
