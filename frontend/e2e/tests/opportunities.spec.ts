import { test, expect } from "../fixtures/auth";

test.describe("Opportunities Page", () => {
  test("page loads with header and description", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/opportunities");

    await expect(page.locator("h1")).toContainText("Opportunities");
    await expect(
      page.getByText("Track and manage government contract opportunities")
    ).toBeVisible();
  });

  test("search input is functional", async ({ authenticatedPage: page }) => {
    await page.goto("/opportunities");

    const searchInput = page.getByPlaceholder("Search opportunities...");
    await expect(searchInput).toBeVisible();
    await searchInput.fill("test query");
    await expect(searchInput).toHaveValue("test query");
  });

  test("action buttons are visible", async ({ authenticatedPage: page }) => {
    await page.goto("/opportunities");

    await expect(
      page.getByRole("button", { name: /Sync SAM\.gov/i })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Add RFP/i })
    ).toBeVisible();
  });
});
