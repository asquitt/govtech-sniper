import { test, expect } from "../fixtures/auth";

test.describe("Compliance Readiness", () => {
  test("shows certification and listing readiness programs", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/compliance");
    await expect(page.getByRole("heading", { name: "Compliance Dashboard" })).toBeVisible();
    await expect(page.getByText("Certification and Listing Readiness")).toBeVisible();
    await expect(page.getByText("FedRAMP Moderate")).toBeVisible();
    await expect(page.getByText("Salesforce AppExchange Listing")).toBeVisible();
    await expect(page.getByText("Microsoft AppSource Listing")).toBeVisible();
  });
});
