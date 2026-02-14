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

async function createBudgetIntel(
  page: Parameters<typeof test>[0]["authenticatedPage"],
  title: string,
) {
  const token = await getAccessToken(page);
  const response = await page.request.post("/api/budget-intel", {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    data: {
      title,
      fiscal_year: 2026,
      amount: 1500000,
      notes: "Cloud modernization and AI readiness priorities.",
      source_url: "https://example.com/e2e-budget",
    },
  });
  expect(response.ok()).toBeTruthy();
}

test.describe("Signals and Events Workflow", () => {
  test("updates signal subscription and marks feed item read", async ({
    authenticatedPage: page,
  }) => {
    const nonce = Date.now();
    const title = `Budget Signal ${nonce}`;
    const signalId = await createSignal(page, title);
    await createBudgetIntel(page, `Budget Intel ${nonce}`);

    await page.goto("/signals");
    await expect(page.getByRole("heading", { name: "Market Signals" })).toBeVisible();
    await expect(page.getByText(title)).toBeVisible();

    await page.getByRole("button", { name: "Subscription Settings" }).click();
    await page
      .getByPlaceholder("cybersecurity, cloud, AI/ML")
      .fill("cloud modernization, ai readiness");
    await page.getByLabel("Enable market signals email digest").check();
    await page.getByRole("button", { name: "Save Preferences" }).click();
    await expect(
      page.getByRole("button", { name: "Subscription Settings" })
    ).toBeVisible();

    await page.getByRole("button", { name: "Ingest News" }).click();
    await expect(page.getByTestId("signals-action-message")).toContainText(
      "News ingestion completed"
    );

    await page.getByRole("button", { name: "Analyze Budget Docs" }).click();
    await expect(page.getByTestId("signals-action-message")).toContainText(
      "Budget analysis completed"
    );

    await page.getByRole("button", { name: "Rescore Signals" }).click();
    await expect(page.getByTestId("signals-action-message")).toContainText(
      "Signals rescored"
    );

    await page.getByRole("button", { name: "Preview Digest" }).click();
    await expect(page.getByTestId("signals-digest-preview-card")).toBeVisible();

    await page.getByRole("button", { name: "Send Digest" }).click();
    await expect(page.getByTestId("signals-action-message")).toContainText("Digest sent to");

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

    await page.getByRole("button", { name: "Budget", exact: true }).click();
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
    await expect(page.getByTestId("events-alerts-card")).toBeVisible();

    await page.getByRole("button", { name: "Ingest from Sources" }).click();
    await expect(page.getByTestId("events-ingest-summary")).toContainText("Ingestion completed");

    await page.getByRole("button", { name: "Calendar" }).click();
    await expect(page.getByTestId("events-calendar-card")).toBeVisible();
    await expect(page.getByTestId("events-calendar-grid")).toBeVisible();

    await page.getByRole("button", { name: "Add Event" }).click();
    await page.getByPlaceholder("Event title").fill(eventTitle);
    await page.locator("input[type='datetime-local']").fill(localDateTime);
    await page.getByPlaceholder("Agency").fill("E2E Events Agency");
    await page.getByPlaceholder("Location").fill("Washington, DC");
    await page.getByPlaceholder("Description (optional)").fill("E2E event workflow check");
    await page.getByRole("button", { name: "Create Event" }).click();

    await page.getByRole("button", { name: "All Events" }).click();
    const createdEventRow = page
      .getByTestId("event-list-row")
      .filter({ has: page.getByText(eventTitle, { exact: true }) })
      .first();
    await expect(createdEventRow).toBeVisible({ timeout: 15_000 });

    await expect(createdEventRow).toBeVisible();

    const eventRow = page
      .getByTestId("event-list-row")
      .filter({ has: page.getByText(eventTitle, { exact: true }) })
      .first();
    await eventRow.getByRole("button", { name: "Delete" }).click();
    await expect(eventRow).toBeHidden({ timeout: 15_000 });
  });
});
