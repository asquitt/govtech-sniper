import { test, expect } from "../fixtures/auth";

test.describe("Compliance Readiness", () => {
  test("shows certification readiness and trust-center guarantees", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/compliance");
    await expect(page.getByRole("heading", { name: "Compliance Dashboard" })).toBeVisible();
    await expect(page.getByText("Certification and Listing Readiness")).toBeVisible();
    await expect(page.getByText("AI & Data Trust Center")).toBeVisible();
    await expect(page.getByText("No model training enforced")).toBeVisible();
    await expect(page.getByText("FedRAMP Moderate", { exact: true })).toBeVisible();
    await expect(page.getByText("Salesforce AppExchange Listing")).toBeVisible();
    await expect(page.getByText("Microsoft AppSource Listing")).toBeVisible();
    const readonlyPolicyNotice = page.getByText(
      "Visibility is enabled for all users. Organization owners/admins can edit these controls."
    );
    const savePolicyControlsButton = page.getByRole("button", { name: /Save policy controls/i });
    await expect
      .poll(async () => {
        const readonlyNoticeCount = await readonlyPolicyNotice.count();
        const saveButtonCount = await savePolicyControlsButton.count();
        return readonlyNoticeCount + saveButtonCount;
      })
      .toBeGreaterThan(0);
    if (await readonlyPolicyNotice.count()) {
      await expect(readonlyPolicyNotice).toBeVisible();
    }
    if (await savePolicyControlsButton.count()) {
      await expect(savePolicyControlsButton).toBeVisible();
    }
    await expect(page.getByRole("button", { name: "Export Trust Evidence" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Public Trust Center ↗" })).toBeVisible();

    await page.goto("/trust-center");
    await expect(
      page.getByRole("heading", { name: "Data Isolation and AI Usage Guarantees" })
    ).toBeVisible();
    await expect(
      page.getByText("Customer proposal content is never used to train third-party AI models")
    ).toBeVisible();
  });
});
