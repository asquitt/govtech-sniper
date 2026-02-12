import { test, expect } from "../fixtures/auth";

test.describe("Mobile Dash", () => {
  test("renders dash chat controls at mobile viewport", async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/dash");

    await expect(page.getByRole("heading", { name: "Dash", exact: true })).toBeVisible();
    await expect(page.getByPlaceholder("Ask Dash a question...")).toBeVisible();
    await expect(page.getByRole("button", { name: /Voice|Sound/ }).first()).toBeVisible();

    const bodyWidth = await page.evaluate(() => document.body.scrollWidth <= window.innerWidth + 8);
    expect(bodyWidth).toBeTruthy();
  });
});
