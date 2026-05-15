# Testing Guide

The project now has a baseline test strategy for backend APIs and browser-level
frontend checks.

## Backend Tests

Backend tests use `pytest`, FastAPI `TestClient`, and an isolated in-memory
SQLite database. They do not touch the local development database.

Run from the repo root:

```bash
cd backend
pytest
```

Current coverage starts with artifact provider readiness because that is the
newest integration boundary.

## Frontend And E2E Tests

E2E tests use Playwright and default to your installed Google Chrome through the
`chrome` browser channel. The npm script starts both servers:

- FastAPI backend on `http://127.0.0.1:8100`
- Next.js frontend on `http://127.0.0.1:3100`
- an isolated migrated SQLite database under `frontend/test-results/`

Run from the repo root:

```bash
cd frontend
npm run test:e2e
```

Useful variants:

```bash
npm run test:e2e:headed
npm run test:e2e:debug
```

Playwright writes failure screenshots and traces under
`frontend/test-results/`. The smoke tests also save full-page screenshots under
`frontend/test-results/manual-screenshots/` so we can inspect what the UI really
rendered.

The PowerShell runner stops only the backend/frontend processes it started. To
use Playwright's built-in `webServer` handling instead, run:

```powershell
$env:E2E_START_SERVERS="true"
npx playwright test
```

Set `E2E_DATABASE_URL` if you intentionally want browser tests to use a
different test database.

## Browser Choice

The default is real installed Chrome:

```ts
channel: "chrome"
```

Override it when needed:

```bash
PLAYWRIGHT_BROWSER_CHANNEL=msedge npm run test:e2e
```

On Windows PowerShell:

```powershell
$env:PLAYWRIGHT_BROWSER_CHANNEL="msedge"
npm run test:e2e
```

## OAuth And External Providers

Normal automated tests should not depend on live Google, Microsoft, or Zoom
OAuth. Keep those flows behind optional manual smoke tests with dedicated test
accounts. For repeatable tests, mock provider API responses or seed local test
data.

Recommended future test layers:

- unit tests for provider capability parsing
- route tests for calendar and artifact probe endpoints
- Playwright workflows for create meeting, upload, transcription status, and
  meeting detail display
- optional manual OAuth smoke tests that use a dedicated browser profile and
  saved Playwright auth state
