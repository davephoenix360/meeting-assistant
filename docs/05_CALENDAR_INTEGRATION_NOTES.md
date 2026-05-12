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

## What You Will Need For External Providers

- A Google Cloud project for Google Calendar, or a Microsoft Entra app registration for Microsoft Graph/Outlook.
- OAuth client ID and client secret.
- A backend redirect URL, for example `http://localhost:8000/api/calendar/oauth/google/callback`.
- Calendar read scopes approved for your test account.
- A test calendar account with real meeting links and realistic meeting titles.
- A decision on token storage before production use. OAuth refresh tokens should be encrypted at rest.

Check the latest Google and Microsoft provider docs before implementing OAuth because
allowed redirect URLs, consent screen rules, and required scopes can change.
