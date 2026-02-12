import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: Parameters<typeof test>[0]["authenticatedPage"]) {
  const token = await page.evaluate(() =>
    localStorage.getItem("rfp_sniper_access_token")
  );
  expect(token).toBeTruthy();
  return token as string;
}

async function createSignal(page: Parameters<typeof test>[0]["authenticatedPage"], title: string) {
  const token = await getAccessToken(page);
  const response = await page.request.post("/api/signals", {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    data: {
      title,
      signal_type: "budget",
      agency: "E2E Signal Agency",
      content: "Budget priorities updated for cloud and AI programs.",
      relevance_score: 87,
      published_at: new Date().toISOString(),
    },
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  return payload.id as number;
}

test.describe("Signals and Events Workflow", () => {
  test("updates signal subscription and marks feed item read", async ({
    authenticatedPage: page,
  }) => {
    const nonce = Date.now();
    const title = `Budget Signal ${nonce}`;
    const signalId = await createSignal(page, title);

    await page.goto("/signals");
    await expect(page.getByRole("heading", { name: "Market Signals" })).toBeVisible();
    await expect(page.getByText(title)).toBeVisible();

    await page.getByRole("button", { name: "Subscription Settings" }).click();
    await page
      .getByPlaceholder("cybersecurity, cloud, AI/ML")
      .fill("cloud modernization, ai readiness");
    await page.getByRole("button", { name: "Save Preferences" }).click();
    await expect(
      page.getByRole("button", { name: "Subscription Settings" })
    ).toBeVisible();

    const signalRow = page
      .locator(".border.rounded-lg")
      .filter({ has: page.getByText(title) })
      .first();
    await signalRow.click();
    await expect(signalRow.locator(".w-2.h-2.rounded-full.bg-primary")).toHaveCount(0, {
      timeout: 10_000,
    });

    const token = await getAccessToken(page);
    await expect
      .poll(
        async () => {
          const signalsResponse = await page.request.get("/api/signals", {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          if (!signalsResponse.ok()) return false;
          const signals = (await signalsResponse.json()) as Array<{
            id: number;
            is_read: boolean;
          }>;
          return signals.find((item) => item.id === signalId)?.is_read ?? false;
        },
        { timeout: 10_000 }
      )
      .toBeTruthy();

    await page.getByRole("button", { name: "Budget" }).click();
    await expect(page.getByText(title)).toBeVisible();
  });

  test("creates and deletes an event from UI", async ({
    authenticatedPage: page,
  }) => {
    const nonce = Date.now();
    const eventTitle = `Industry Event ${nonce}`;

    const futureDate = new Date(Date.now() + 5 * 24 * 60 * 60 * 1000);
    const localDateTime = `${futureDate.getFullYear()}-${String(
      futureDate.getMonth() + 1
    ).padStart(2, "0")}-${String(futureDate.getDate()).padStart(2, "0")}T${String(
      futureDate.getHours()
    ).padStart(2, "0")}:${String(futureDate.getMinutes()).padStart(2, "0")}`;

    await page.goto("/events");
    await expect(page.getByRole("heading", { name: "Industry Days & Events" })).toBeVisible();

    await page.getByRole("button", { name: "Add Event" }).click();
    await page.getByPlaceholder("Event title").fill(eventTitle);
    await page.locator("input[type='datetime-local']").fill(localDateTime);
    await page.getByPlaceholder("Agency").fill("E2E Events Agency");
    await page.getByPlaceholder("Location").fill("Washington, DC");
    await page.getByPlaceholder("Description (optional)").fill("E2E event workflow check");
    await page.getByRole("button", { name: "Create Event" }).click();

    await expect(page.getByText(eventTitle)).toBeVisible({ timeout: 15_000 });

    await page.getByRole("button", { name: "All Events" }).click();
    await expect(page.getByText(eventTitle)).toBeVisible();

    const eventRow = page
      .locator(".border.rounded-lg")
      .filter({ has: page.getByText(eventTitle) })
      .first();
    await eventRow.getByRole("button", { name: "Delete" }).click();
    await expect(page.getByText(eventTitle)).toBeHidden({ timeout: 15_000 });
  });
});
