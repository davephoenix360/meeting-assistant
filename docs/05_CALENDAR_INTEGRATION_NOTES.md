# Calendar Integration Notes

The current calendar slice is provider-neutral and does not call external APIs yet.
It adds local storage and app APIs for calendar accounts and imported events so Google
Calendar, Microsoft Graph, Outlook, and manual imports can share the same product model.

## What Works Now

- Add calendar account records from `/calendar`.
- Disconnect calendar account records.
- Manually import calendar event records.
- List accounts with `GET /api/calendar/accounts`.
- List/import events with `GET /api/calendar/events` and `POST /api/calendar/events`.
- Check provider readiness with `GET /api/calendar/providers`.
- Build OAuth authorization URLs with `GET /api/calendar/oauth/{provider}/start`.
- Receive OAuth callback codes, exchange them for tokens, and store encrypted token values at `GET /api/calendar/oauth/{provider}/callback`.
- Trigger the provider sync boundary with `POST /api/calendar/accounts/{id}/sync`.

Provider event sync fetches Google Calendar and Microsoft Graph events with the
stored access token and upserts them into `calendar_events`. Sync refreshes stored
access tokens automatically when they are expired or rejected with `401`.

## What You Will Need For External Providers

- A Google Cloud project for Google Calendar, or a Microsoft Entra app registration for Microsoft Graph/Outlook.
- OAuth client ID and client secret.
- A backend redirect URL, for example `http://localhost:8000/api/calendar/oauth/google/callback`.
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
- `GOOGLE_CALENDAR_CLIENT_ID`
- `GOOGLE_CALENDAR_CLIENT_SECRET`
- `MICROSOFT_CALENDAR_CLIENT_ID`
- `MICROSOFT_CALENDAR_CLIENT_SECRET`
- `MICROSOFT_CALENDAR_TENANT`
- `TOKEN_ENCRYPTION_KEY`

Check the latest Google and Microsoft provider docs before implementing OAuth because
allowed redirect URLs, consent screen rules, and required scopes can change.
