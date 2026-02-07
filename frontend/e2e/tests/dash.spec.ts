import { test, expect } from "../fixtures/auth";

test.describe("Dash (AI Assistant) Page", () => {
  test("page loads with header", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/dash");

    await expect(page.locator("h1")).toContainText("Dash");
    await expect(
      page.getByText("Your AI assistant for GovCon workflows")
    ).toBeVisible();
  });

  test("suggestion buttons are visible", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/dash");

    await expect(
      page.getByRole("button", { name: "Summarize solicitation" })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Compliance gaps" })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Draft capability statement" })
    ).toBeVisible();
  });

  test("chat input is functional", async ({ authenticatedPage: page }) => {
    await page.goto("/dash");

    const chatInput = page.getByPlaceholder("Ask Dash a question...");
    await expect(chatInput).toBeVisible();
    await chatInput.fill("What is this opportunity about?");
    await expect(chatInput).toHaveValue("What is this opportunity about?");
  });
});
