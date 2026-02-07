import { test as base, type Page, expect } from "@playwright/test";
import { TEST_USER, STORAGE_KEYS } from "../helpers/constants";

async function registerTestUser(page: Page): Promise<boolean> {
  await page.goto("/register");
  await page.getByLabel("Full Name").fill(TEST_USER.fullName);
  await page.getByLabel("Email").fill(TEST_USER.email);
  await page.getByLabel("Company Name").fill(TEST_USER.companyName);
  await page.getByLabel("Password", { exact: true }).fill(TEST_USER.password);
  await page.getByLabel("Confirm Password").fill(TEST_USER.password);
  await page.getByRole("button", { name: "Create account" }).click();

  const result = await Promise.race([
    page
      .waitForURL("**/opportunities", { timeout: 15_000 })
      .then(() => "success" as const),
    page
      .locator("[class*='destructive']")
      .first()
      .waitFor({ timeout: 15_000 })
      .then(() => "error" as const),
  ]);

  return result === "success";
}

async function loginTestUser(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(TEST_USER.email);
  await page.getByLabel("Password", { exact: true }).fill(TEST_USER.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/opportunities", { timeout: 15_000 });
}

export async function loginAsTestUser(page: Page): Promise<void> {
  const registered = await registerTestUser(page);
  if (!registered) {
    await loginTestUser(page);
  }
  const token = await page.evaluate(
    (key) => localStorage.getItem(key),
    STORAGE_KEYS.accessToken
  );
  expect(token).toBeTruthy();
}

export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use) => {
    await loginAsTestUser(page);
    await use(page);
  },
});

export { expect } from "@playwright/test";
