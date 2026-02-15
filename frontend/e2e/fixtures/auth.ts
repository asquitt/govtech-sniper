import { test as base, type Page } from "@playwright/test";
import { TEST_USER, STORAGE_KEYS } from "../helpers/constants";

let cachedAuth: { accessToken: string; refreshToken: string | null } | null = null;

async function fillIfVisible(page: Page, label: RegExp | string, value: string): Promise<void> {
  const locator = page.getByLabel(label).first();
  if (await locator.count()) {
    try {
      await locator.fill(value, { timeout: 2000 });
    } catch {
      // optional field in some auth surfaces
    }
  }
}

async function waitForAuthenticatedLanding(page: Page): Promise<void> {
  await Promise.race([
    page.waitForURL("**/opportunities", { timeout: 15_000 }),
    page.waitForURL("**/onboarding", { timeout: 15_000 }),
  ]);
}

async function registerTestUser(page: Page): Promise<boolean> {
  await page.goto("/register");
  await fillIfVisible(page, /Full Name/i, TEST_USER.fullName);
  await fillIfVisible(page, /Email/i, TEST_USER.email);
  await fillIfVisible(page, /Company Name/i, TEST_USER.companyName);
  await fillIfVisible(page, /^Password$/i, TEST_USER.password);
  await fillIfVisible(page, /Confirm Password/i, TEST_USER.password);

  const acceptCookies = page.getByRole("button", { name: /Accept All/i }).first();
  if (await acceptCookies.count()) {
    try {
      await acceptCookies.click({ timeout: 1000 });
    } catch {
      // non-blocking
    }
  }

  const createAccountButton = page.getByRole("button", { name: /Create account/i }).first();
  if (!(await createAccountButton.count())) {
    return false;
  }
  await createAccountButton.click();

  const result = await Promise.race([
    waitForAuthenticatedLanding(page).then(() => "success" as const),
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
  await waitForAuthenticatedLanding(page);
}

async function restoreCachedSession(page: Page): Promise<boolean> {
  if (!cachedAuth?.accessToken) return false;

  await page.goto("/login");
  await page.evaluate(
    ({ keys, accessToken, refreshToken }) => {
      localStorage.setItem(keys.accessToken, accessToken);
      if (refreshToken) {
        localStorage.setItem(keys.refreshToken, refreshToken);
      }
    },
    {
      keys: STORAGE_KEYS,
      accessToken: cachedAuth.accessToken,
      refreshToken: cachedAuth.refreshToken,
    }
  );

  await page.goto("/opportunities");
  return !page.url().includes("/login");
}

export async function loginAsTestUser(page: Page): Promise<void> {
  if (await restoreCachedSession(page)) {
    return;
  }

  const registered = await registerTestUser(page);
  if (!registered) {
    await loginTestUser(page);
  }

  const authState = await page.evaluate(
    (keys) => ({
      accessToken: localStorage.getItem(keys.accessToken),
      refreshToken: localStorage.getItem(keys.refreshToken),
    }),
    STORAGE_KEYS
  );
  if (!authState.accessToken) {
    cachedAuth = null;
    return;
  }

  cachedAuth = {
    accessToken: authState.accessToken!,
    refreshToken: authState.refreshToken,
  };
}

export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use) => {
    await loginAsTestUser(page);
    await use(page);
  },
});

export { expect } from "@playwright/test";
