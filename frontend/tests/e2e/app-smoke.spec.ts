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
