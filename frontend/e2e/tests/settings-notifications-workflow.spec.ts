import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: any): Promise<string> {
  const token = await page.evaluate(() => localStorage.getItem("rfp_sniper_access_token"));
  expect(token).toBeTruthy();
  return token as string;
}

test.describe("Settings Notifications Workflow", () => {
  test("manages push subscriptions from settings page", async ({
    authenticatedPage: page,
  }) => {
    const token = await getAccessToken(page);
    const endpoint = `browser://playwright/${Date.now()}`;

    const create = await page.request.post("/api/notifications/push-subscriptions", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        endpoint,
        p256dh_key: "test-public-key",
        auth_key: "test-auth-key",
        user_agent: "Playwright",
      },
    });
    expect(create.ok()).toBeTruthy();

    await page.goto("/settings/notifications");
    await expect(page.getByRole("heading", { name: "Notification Settings" })).toBeVisible();
    await expect(page.getByText(endpoint)).toBeVisible({ timeout: 10_000 });

    await page.getByRole("button", { name: "Enable Push Notifications" }).click();

    const subscriptionRow = page.locator("div").filter({ hasText: endpoint }).first();
    await subscriptionRow.getByRole("button", { name: "Remove" }).click();
    await expect(page.getByText(endpoint)).not.toBeVisible({ timeout: 10_000 });
  });
});
