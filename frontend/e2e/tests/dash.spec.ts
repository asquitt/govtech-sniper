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

    const promptCard = page
      .locator("div")
      .filter({ has: page.getByRole("heading", { name: "Ask Dash anything" }) })
      .first();
    const suggestionButtons = promptCard.getByRole("button");
    await expect(suggestionButtons.first()).toBeVisible();
    const suggestionCount = await suggestionButtons.count();
    expect(suggestionCount).toBeGreaterThanOrEqual(3);
  });

  test("chat input is functional", async ({ authenticatedPage: page }) => {
    await page.goto("/dash");

    const chatInput = page.getByPlaceholder("Ask Dash a question...");
    await expect(chatInput).toBeVisible();
    await chatInput.fill("What is this opportunity about?");
    await expect(chatInput).toHaveValue("What is this opportunity about?");
  });

  test("voice controls are surfaced in the chat input bar", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/dash");

    const voiceControl = page.getByRole("button", { name: /Voice|Sound/ }).first();
    await expect(voiceControl).toBeVisible();
  });
});
