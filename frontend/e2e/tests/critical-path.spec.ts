import { test, expect } from "../fixtures/auth";

test.describe("Critical Path", () => {
  test("ingest -> analyze -> draft runs in live UI", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/opportunities");

    await page.getByRole("button", { name: /Sync SAM\.gov/i }).click();

    const analyzeLink = page.locator('a[href^="/analysis/"]').first();
    await expect(analyzeLink).toBeVisible({ timeout: 20_000 });
    await analyzeLink.click();

    await expect(page.getByRole("button", { name: "Add Requirement" })).toBeVisible();
    await page.getByRole("button", { name: "Add Requirement" }).click();

    const addPanel = page
      .locator("div")
      .filter({ hasText: "Insert a new requirement into the matrix" })
      .first();
    await addPanel.locator("input").first().fill("L.1");
    await addPanel
      .locator("textarea")
      .first()
      .fill("Provide a technical implementation plan for this requirement.");
    await addPanel.getByRole("button", { name: "Add", exact: true }).click();

    const generateButton = page.getByRole("button", { name: "Generate" }).first();
    await expect(generateButton).toBeVisible();
    await generateButton.click();

    await expect(page.getByRole("heading", { name: "Error" })).toHaveCount(0);
    await expect(
      page.getByText("This is a mock response generated for testing purposes.")
    ).toBeVisible({ timeout: 20_000 });
  });
});
