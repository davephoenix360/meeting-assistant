# Calendar Integration Notes

The calendar slice is provider-neutral and can connect to Google Calendar and
Microsoft Graph through OAuth. Local/manual imports still use the same product
model so future providers do not force a rewrite.

## What Works Now

- Add calendar account records from `/calendar`.
- Disconnect calendar account records.
- Manually import calendar event records.
- List accounts with `GET /api/calendar/accounts`.
- List/import events with `GET /api/calendar/events` and `POST /api/calendar/events`.
- Check provider readiness with `GET /api/calendar/providers`.
- Check account sync status with `GET /api/calendar/sync-status`.
- Start OAuth with `GET /api/calendar/oauth/{provider}/start`; browser requests redirect to the provider, and `?as_json=true` returns the authorization payload for debugging.
- Receive OAuth callback codes, exchange them for tokens, store encrypted token values, and redirect back to `/calendar`.
- Trigger the provider sync boundary with `POST /api/calendar/accounts/{id}/sync`.
- Create linked meeting records from imported events with `POST /api/calendar/events/{id}/create-meeting`.

Provider event sync fetches Google Calendar and Microsoft Graph events with the
stored access token and upserts them into `calendar_events`. Sync refreshes stored
access tokens automatically when they are expired or rejected with `401`.
Imported events can create meeting records. The event remains linked through
`calendar_events.imported_meeting_id`.

The `/calendar` page auto-syncs connected OAuth accounts every five minutes while
the page is open. The backend also starts an in-process background sync loop for
connected OAuth accounts so events can refresh even when no browser is open. This
is still an MVP scheduler; production deployments should use a single durable
worker or queue so multi-process servers do not run duplicate loops.
Calendar account rows show the latest sync time, last result counts, and the last
background sync error when one exists.

## What You Will Need For External Providers

- A Google Cloud project for Google Calendar, or a Microsoft Entra app registration for Microsoft Graph/Outlook.
- OAuth client ID and client secret.
- A backend redirect URL, for example `http://localhost:8000/api/calendar/oauth/google/callback`.
- A frontend return URL, for example `http://localhost:3000/calendar`.
- Calendar read scopes approved for your test account.
  - Google default: `https://www.googleapis.com/auth/calendar.events.readonly`.
  - Microsoft default: `Calendars.Read` plus `offline_access` for refresh tokens.
- A test calendar account with real meeting links and realistic meeting titles.
- `TOKEN_ENCRYPTION_KEY` configured before OAuth callbacks can store tokens.
- A production decision on stronger managed key storage. The local implementation
  encrypts token values before database persistence, but a hosted deployment should
  use a managed secret/KMS approach.

## Environment Variables

- `BACKEND_PUBLIC_URL`
- `FRONTEND_PUBLIC_URL`
- `GOOGLE_CALENDAR_CLIENT_ID`
- `GOOGLE_CALENDAR_CLIENT_SECRET`
- `MICROSOFT_CALENDAR_CLIENT_ID`
- `MICROSOFT_CALENDAR_CLIENT_SECRET`
- `MICROSOFT_CALENDAR_TENANT`
- `CALENDAR_BACKGROUND_SYNC_ENABLED`
- `CALENDAR_BACKGROUND_SYNC_INTERVAL_SECONDS`
- `CALENDAR_BACKGROUND_SYNC_DAYS_BACK`
- `CALENDAR_BACKGROUND_SYNC_DAYS_FORWARD`
- `CALENDAR_BACKGROUND_SYNC_MAX_RESULTS`
- `CALENDAR_BACKGROUND_SYNC_MAX_PAGES`
- `TOKEN_ENCRYPTION_KEY`

Check the latest Google and Microsoft provider docs before implementing OAuth because
allowed redirect URLs, consent screen rules, and required scopes can change.

Calendar scopes do not grant recording or transcript access. See
`docs/06_PROVIDER_ARTIFACT_PERMISSIONS.md` before adding provider-specific
artifact imports.
