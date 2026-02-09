import { test, expect } from "@playwright/test";
import { STORAGE_KEYS } from "../helpers/constants";

const UNIQUE_EMAIL = `e2e-auth-${Date.now()}@example.com`;
const PASSWORD = "AuthTest1!";
const FULL_NAME = "Auth Test User";

test.describe("Authentication Flow", () => {
  test("register a new user and land on opportunities", async ({ page }) => {
    await page.goto("/register");

    await page.getByLabel("Full Name").fill(FULL_NAME);
    await page.getByLabel("Email").fill(UNIQUE_EMAIL);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByLabel("Confirm Password").fill(PASSWORD);

    await expect(page.getByText("At least 8 characters")).toBeVisible();
    await expect(page.getByText("Contains special character")).toBeVisible();

    await page.getByRole("button", { name: "Create account" }).click();

    await page.waitForURL("**/opportunities", { timeout: 15_000 });
    await expect(page.locator("h1")).toContainText("Opportunities");

    const token = await page.evaluate(
      (key) => localStorage.getItem(key),
      STORAGE_KEYS.accessToken
    );
    expect(token).toBeTruthy();
  });

  test("login with existing user and see dashboard", async ({ page }) => {
    await page.goto("/login");

    await expect(page.getByText("Welcome back")).toBeVisible();

    await page.getByLabel("Email").fill(UNIQUE_EMAIL);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();

    await page.waitForURL("**/opportunities", { timeout: 15_000 });
    await expect(page.locator("h1")).toContainText("Opportunities");
  });

  test("logout returns to login page", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(UNIQUE_EMAIL);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL("**/opportunities", { timeout: 15_000 });

    const logoutButton = page.locator("aside button").filter({
      has: page.locator("svg.lucide-log-out"),
    });
    await logoutButton.click();

    await page.waitForURL("**/login", { timeout: 10_000 });
    await expect(page.getByText("Welcome back")).toBeVisible();

    const token = await page.evaluate(
      (key) => localStorage.getItem(key),
      STORAGE_KEYS.accessToken
    );
    expect(token).toBeNull();
  });

  test("unauthenticated user is redirected to login", async ({ page }) => {
    await page.goto("/login");
    await page.evaluate(() => localStorage.clear());

    await page.goto("/opportunities");

    await page.waitForURL("**/login", { timeout: 10_000 });
  });
});
