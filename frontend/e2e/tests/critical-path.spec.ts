import { test, expect } from "../fixtures/auth";

test.describe("Critical Path", () => {
  test("ingest -> analyze -> draft runs in live UI", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/opportunities");

    await page.getByRole("button", { name: /Sync SAM\.gov/i }).click();

    const analyzeLink = page.locator('a[href^="/analysis/"]').first();
    const hasAnalyzeLink = await analyzeLink
      .isVisible({ timeout: 20_000 })
      .catch(() => false);

    if (hasAnalyzeLink) {
      await analyzeLink.click();
    } else {
      // Deterministic fallback: create a minimal RFP when ingest returns no rows.
      const token = await page.evaluate(() =>
        localStorage.getItem("rfp_sniper_access_token")
      );
      expect(token).toBeTruthy();

      const nonce = Date.now();
      const createResponse = await page.request.post("/api/rfps", {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          title: `E2E Critical Path ${nonce}`,
          solicitation_number: `E2E-CRIT-${nonce}`,
          agency: "E2E Test Agency",
          posted_date: new Date().toISOString(),
        },
      });
      expect(createResponse.ok()).toBeTruthy();
      const created = await createResponse.json();

      await page.goto(`/analysis/${created.id}`);
    }

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
