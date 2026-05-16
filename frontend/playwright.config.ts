import { defineConfig, devices } from "@playwright/test";

const frontendPort = Number(process.env.E2E_FRONTEND_PORT || 3100);
const backendPort = Number(process.env.E2E_BACKEND_PORT || 8100);
const baseURL = process.env.E2E_BASE_URL || `http://127.0.0.1:${frontendPort}`;
const apiBaseURL =
  process.env.NEXT_PUBLIC_API_BASE_URL || `http://127.0.0.1:${backendPort}/api`;
const corsOrigins =
  process.env.CORS_ORIGINS ||
  `${baseURL},http://localhost:${frontendPort},http://127.0.0.1:3000,http://localhost:3000`;
const shouldStartServers = process.env.E2E_START_SERVERS !== "false";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  outputDir: "test-results",
  use: {
    baseURL,
    channel: process.env.PLAYWRIGHT_BROWSER_CHANNEL || "chrome",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
  },
  webServer: shouldStartServers
    ? [
        {
          command: `python -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
          cwd: "../backend",
          env: {
            CALENDAR_BACKGROUND_SYNC_ENABLED: "false",
            CORS_ORIGINS: corsOrigins,
            FRONTEND_PUBLIC_URL: baseURL,
            BACKEND_PUBLIC_URL: `http://127.0.0.1:${backendPort}`,
          },
          reuseExistingServer: true,
          timeout: 30_000,
          url: `http://127.0.0.1:${backendPort}/api/artifacts/providers/status`,
        },
        {
          command: `npx next dev --hostname 127.0.0.1 --port ${frontendPort}`,
          env: {
            NEXT_PUBLIC_API_BASE_URL: apiBaseURL,
          },
          reuseExistingServer: true,
          timeout: 60_000,
          url: baseURL,
        },
      ]
    : undefined,
  projects: [
    {
      name: "chrome-desktop",
      use: {
        ...devices["Desktop Chrome"],
      },
    },
  ],
});
