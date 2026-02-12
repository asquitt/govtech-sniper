import { test, expect } from "../fixtures/auth";

test.describe("Settings Page", () => {
  test("main settings page loads", async ({ authenticatedPage: page }) => {
    await page.goto("/settings");

    await expect(page.locator("h1")).toContainText("Settings");
    await expect(
      page.getByText("Manage integrations and admin configuration")
    ).toBeVisible();
  });

  test("integrations section is visible", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/settings");

    await expect(
      page.getByText("Integrations", { exact: true })
    ).toBeVisible();
  });

  test("data-sources sub-page loads", async ({ authenticatedPage: page }) => {
    await page.goto("/settings/data-sources");

    await expect(page.locator("h1").first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("SLED (BidNet)")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("DIBBS")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("OASIS+", { exact: true })).toBeVisible({ timeout: 10_000 });
    const body = page.locator("body");
    await expect(body).not.toContainText("Unhandled Runtime Error");
  });

  test("email-ingest sub-page loads", async ({ authenticatedPage: page }) => {
    await page.goto("/settings/email-ingest");

    await expect(page.locator("h1").first()).toBeVisible({ timeout: 10_000 });
    const body = page.locator("body");
    await expect(body).not.toContainText("Unhandled Runtime Error");
  });

  test("subscription sub-page loads", async ({ authenticatedPage: page }) => {
    await page.goto("/settings/subscription");

    await expect(page.locator("h1").first()).toBeVisible({ timeout: 10_000 });
    const body = page.locator("body");
    await expect(body).not.toContainText("Unhandled Runtime Error");
  });

  test("workflows sub-page loads", async ({ authenticatedPage: page }) => {
    await page.goto("/settings/workflows");

    await expect(page.locator("h1").first()).toBeVisible({ timeout: 10_000 });
    const body = page.locator("body");
    await expect(body).not.toContainText("Unhandled Runtime Error");
  });

  test("notifications sub-page loads", async ({ authenticatedPage: page }) => {
    await page.goto("/settings/notifications");

    await expect(page.locator("h1").first()).toBeVisible({ timeout: 10_000 });
    const body = page.locator("body");
    await expect(body).not.toContainText("Unhandled Runtime Error");
  });
});
