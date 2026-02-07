import { test, expect } from "../fixtures/auth";

test.describe("Proposals Page", () => {
  test("page loads with header", async ({ authenticatedPage: page }) => {
    await page.goto("/proposals");

    await expect(page.locator("h1")).toContainText("Proposals");
    await expect(page.getByText("Manage proposal drafts")).toBeVisible();
  });

  test("shows empty state or proposal list", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/proposals");

    // Wait for page content to load, then check for either state
    await expect(
      page
        .getByText("No proposals yet.")
        .or(page.getByText("Open Workspace").first())
    ).toBeVisible();
  });
});
