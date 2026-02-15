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
    await expect(
      page.getByText(
        "Visibility is enabled for all users. Organization owners/admins can edit these controls."
      )
    ).toBeVisible();
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
