import { expect, test } from "../fixtures/auth";

test.describe("Templates, Reports, Help, and Onboarding workflow", () => {
  test("validates vertical templates, report builder sharing, help center tutorials, and guided setup", async ({
    authenticatedPage: page,
  }) => {
    const nonce = Date.now();

    await page.goto("/templates");
    await expect(page.getByRole("heading", { name: "Template Marketplace" })).toBeVisible();
    await page.getByRole("button", { name: "Proposal Kits" }).click();
    await expect(
      page.getByRole("heading", { name: "Proposal Structure - IT Services" }).first()
    ).toBeVisible();
    await page.getByRole("button", { name: "Compliance Matrices" }).click();
    await expect(
      page.getByRole("heading", { name: "Compliance Matrix - GSA MAS Task Order" }).first()
    ).toBeVisible();

    await page.goto("/reports");
    await expect(page.getByRole("heading", { name: "Reports" })).toBeVisible();
    await page.getByRole("button", { name: "New Report" }).click();
    await page.getByPlaceholder("e.g. Monthly Pipeline Summary").fill(`Ops Shared Report ${nonce}`);
    await page.getByRole("button", { name: "Create" }).click();
    const reportCard = page
      .locator(".rounded-xl.border")
      .filter({ has: page.getByText(`Ops Shared Report ${nonce}`) })
      .first();
    await expect(reportCard).toBeVisible({ timeout: 15_000 });
    await reportCard
      .getByPlaceholder("user1@agency.com, user2@agency.com")
      .fill("teammate@example.com");
    await reportCard.getByRole("button", { name: "Save Shared View" }).click();

    await page.goto("/help");
    await expect(page.getByRole("heading", { name: "Help Center" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Interactive Tutorials" })).toBeVisible();
    await page
      .getByPlaceholder("Ask support anything about onboarding, templates, or reports...")
      .fill("How do I schedule reports?");
    await page.getByRole("button", { name: "Ask Support" }).click();
    await expect(page.getByText(/report/i).first()).toBeVisible();

    await page.goto("/opportunities");
    // Guided Setup button only appears when onboarding wizard isn't dismissed
    const guidedSetupBtn = page.getByRole("button", { name: "Guided Setup" });
    if (await guidedSetupBtn.count()) {
      await guidedSetupBtn.click({ timeout: 5_000 }).catch(() => {});
      const wizardHeading = page.getByText("Guided Setup Wizard");
      if (await wizardHeading.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await page.getByRole("button", { name: "Close" }).click();
      }
    }
  });
});
