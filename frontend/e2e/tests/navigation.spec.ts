import { test, expect } from "../fixtures/auth";
import { NAV_ITEMS } from "../helpers/constants";

test.describe("Sidebar Navigation", () => {
  const CRITICAL_NAV = NAV_ITEMS.filter((item) =>
    [
      "/opportunities",
      "/proposals",
      "/dash",
      "/settings",
      "/analytics",
      "/pipeline",
    ].includes(item.href)
  );

  for (const navItem of CRITICAL_NAV) {
    test(`navigates to ${navItem.title} (${navItem.href})`, async ({
      authenticatedPage: page,
    }) => {
      const sidebarLink = page
        .locator("aside")
        .getByRole("link", { name: navItem.title });
      await sidebarLink.click();

      await expect(page).toHaveURL(new RegExp(navItem.href));

      await expect(page.locator("h1").first()).toBeVisible({ timeout: 10_000 });

      const body = page.locator("body");
      await expect(body).not.toContainText("Application error");
      await expect(body).not.toContainText("Unhandled Runtime Error");
    });
  }

  test("sidebar shows system status", async ({
    authenticatedPage: page,
  }) => {
    const sidebar = page.locator("aside");
    await expect(sidebar).toBeVisible();
    await expect(sidebar.getByText("System Online")).toBeVisible();
  });

  test("sidebar collapse toggle works", async ({
    authenticatedPage: page,
  }) => {
    const sidebar = page.locator("aside");

    await expect(sidebar.getByText("Collapse")).toBeVisible();

    await sidebar.getByText("Collapse").click();

    await expect(sidebar.getByText("Collapse")).not.toBeVisible();
    await expect(sidebar).toBeVisible();
  });
});
