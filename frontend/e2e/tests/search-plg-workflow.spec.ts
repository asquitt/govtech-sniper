import { test, expect } from "../fixtures/auth";

test.describe("Search + PLG Workflow", () => {
  test("opens global search from header and toggles facets", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/opportunities");

    await page.getByLabel("Open global search").click();
    const dialog = page.getByTestId("global-search-dialog");
    await expect(dialog).toBeVisible();

    const input = page.getByTestId("global-search-input");
    await input.fill("cyber");
    await expect(input).toHaveValue("cyber");

    await page.getByRole("button", { name: "Opportunities" }).click();
    await page.getByRole("button", { name: "Proposal Sections" }).click();
    await page.getByRole("button", { name: "Knowledge Base" }).click();
    await expect(page.getByRole("button", { name: "Contacts" })).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });

  test("loads the free-tier landing page and signup CTA", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/free-tier");

    await expect(
      page.getByRole("heading", { name: "Start winning contracts with zero upfront cost" })
    ).toBeVisible();
    await expect(page.getByRole("link", { name: "Create Free Account" })).toBeVisible();
    await expect(page.getByText("Included at No Cost")).toBeVisible();
  });
});
