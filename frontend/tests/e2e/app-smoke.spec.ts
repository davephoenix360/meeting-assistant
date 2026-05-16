import { expect, test, type Page } from "@playwright/test";

async function capture(page: Page, name: string) {
  await page.screenshot({
    fullPage: true,
    path: `test-results/manual-screenshots/${name}.png`,
  });
}

test("renders the home page navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: /Meeting Assistant/i })).toBeVisible();
  await expect(page.getByRole("link", { name: "Meetings" })).toBeVisible();
  await capture(page, "home");
});

test("renders the meetings library", async ({ page }) => {
  await page.goto("/meetings");
  await expect(page.getByRole("heading", { name: "Meetings", exact: true })).toBeVisible();
  await capture(page, "meetings");
});

test("renders the settings page", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await capture(page, "settings");
});

test("shows artifact readiness status on the calendar page", async ({ page }) => {
  await page.goto("/calendar");

  await expect(page.getByText("Google Meet artifacts", { exact: true })).toBeVisible();
  await expect(page.getByText("Microsoft Teams artifacts", { exact: true })).toBeVisible();
  await expect(page.getByText("Zoom cloud artifacts", { exact: true })).toBeVisible();
  await capture(page, "artifact-readiness");
});

test("shows Google Meet probe state on meeting detail", async ({ page, request }) => {
  const backendBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8100/api";
  const accountResponse = await request.post("http://127.0.0.1:8100/api/calendar/accounts", {
    data: {
      workspace_id: 1,
      provider: "google",
      account_email: "probe@example.com",
      display_name: "Probe account",
      scopes: [],
      provider_metadata: { source: "e2e" },
    },
  });
  expect(accountResponse.ok()).toBeTruthy();
  const account = await accountResponse.json();

  const eventResponse = await request.post("http://127.0.0.1:8100/api/calendar/events", {
    data: {
      calendar_account_id: account.id,
      external_event_id: "probe-event",
      title: "Probe event",
      meeting_url: "https://meet.google.com/abc-defg-hij",
      raw: { source: "e2e" },
    },
  });
  expect(eventResponse.ok()).toBeTruthy();
  const event = await eventResponse.json();

  const meetingResponse = await request.post(
    `http://127.0.0.1:8100/api/calendar/events/${event.id}/create-meeting`,
    { data: { tags: ["calendar"] } },
  );
  expect(meetingResponse.ok()).toBeTruthy();
  const meetingEvent = await meetingResponse.json();
  expect(meetingEvent.imported_meeting_id).toBeTruthy();

  const linkedMeetingId = Number(meetingEvent.imported_meeting_id);
  const detailResponse = await request.get(`${backendBaseUrl}/meetings/${linkedMeetingId}`);
  expect(detailResponse.ok()).toBeTruthy();

  await page.goto(`/meetings/${linkedMeetingId}`);
  await expect(page.getByRole("heading", { level: 2, name: "Probe event" })).toBeVisible();
  await expect(page.getByText("Probe Google Meet", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Run probe" }).click();
  await expect(page.getByText("not connected")).toBeVisible();
  await capture(page, "meeting-google-probe");
});
