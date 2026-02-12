import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: Parameters<typeof test>[0]["authenticatedPage"]) {
  const token = await page.evaluate(() =>
    localStorage.getItem("rfp_sniper_access_token")
  );
  expect(token).toBeTruthy();
  return token as string;
}

async function createRfp(
  page: Parameters<typeof test>[0]["authenticatedPage"],
  title: string,
  agency: string,
  naicsCode: string,
  estimatedValue: number
) {
  const token = await getAccessToken(page);
  const response = await page.request.post("/api/rfps", {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    data: {
      title,
      solicitation_number: `E2E-REV-${Date.now()}`,
      agency,
      naics_code: naicsCode,
      estimated_value: estimatedValue,
      posted_date: new Date().toISOString(),
      response_deadline: new Date(Date.now() + 45 * 24 * 60 * 60 * 1000).toISOString(),
    },
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  return payload.id as number;
}

async function createCapturePlan(
  page: Parameters<typeof test>[0]["authenticatedPage"],
  rfpId: number,
  winProbability: number
) {
  const token = await getAccessToken(page);
  const response = await page.request.post("/api/capture/plans", {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    data: {
      rfp_id: rfpId,
      stage: "pursuit",
      bid_decision: "bid",
      win_probability: winProbability,
    },
  });
  expect(response.ok()).toBeTruthy();
}

async function createContract(
  page: Parameters<typeof test>[0]["authenticatedPage"],
  title: string,
  agency: string,
  value: number
) {
  const token = await getAccessToken(page);
  const response = await page.request.post("/api/contracts", {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    data: {
      contract_number: `E2E-AWD-${Date.now()}`,
      title,
      agency,
      value,
      status: "active",
      start_date: "2026-01-01",
    },
  });
  expect(response.ok()).toBeTruthy();
}

test.describe("Revenue and Forecasts Workflow", () => {
  test("renders revenue cards with seeded pipeline and won value", async ({
    authenticatedPage: page,
  }) => {
    const nonce = Date.now();
    const agency = "E2E Revenue Agency";
    const rfpId = await createRfp(
      page,
      `Revenue RFP ${nonce}`,
      agency,
      "541512",
      1_800_000
    );
    await createCapturePlan(page, rfpId, 65);
    await createContract(page, `Revenue Contract ${nonce}`, agency, 900_000);

    await page.goto("/revenue");

    await expect(page.getByRole("heading", { name: "Revenue Forecasting" })).toBeVisible();
    await expect(
      page.locator("p").filter({ hasText: /^Weighted Pipeline$/ }).first()
    ).toBeVisible();
    await expect(page.locator("p").filter({ hasText: /^Won Revenue$/ }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Revenue by Agency" })).toBeVisible();

    await page.getByRole("button", { name: "Quarterly" }).click();
    await expect(page.getByText("Revenue Timeline (quarterly)")).toBeVisible();
    await expect(page.locator("body")).toContainText("E2E Revenue");
  });

  test("creates a forecast, runs matching, and dismisses alert", async ({
    authenticatedPage: page,
  }) => {
    const nonce = Date.now();
    const agency = "E2E Forecast Agency";
    const forecastTitle = `Cloud Forecast ${nonce}`;

    await createRfp(
      page,
      `Cloud Program ${nonce}`,
      agency,
      "541512",
      2_000_000
    );

    await page.goto("/forecasts");
    await page.getByRole("button", { name: "Add Forecast" }).click();
    await page.getByPlaceholder("Title").fill(forecastTitle);
    await page.getByPlaceholder("Agency").fill(agency);
    await page.getByPlaceholder("NAICS Code").fill("541512");
    await page.getByPlaceholder("Est. Value ($)").fill("1900000");
    await page.getByRole("button", { name: "Create Forecast" }).click();

    await expect(page.getByText(forecastTitle)).toBeVisible();

    await page.getByRole("button", { name: "Run Matching" }).click();
    const alertsCard = page
      .locator(".border")
      .filter({ has: page.getByText("Forecast Alerts", { exact: false }) })
      .first();
    await expect(alertsCard).toBeVisible({ timeout: 15_000 });
    await expect(alertsCard.getByText(forecastTitle).first()).toBeVisible();

    const alertRows = alertsCard.locator(".border.rounded-lg");
    const countBeforeDismiss = await alertRows.count();
    const firstAlertRow = alertRows.first();
    await firstAlertRow.getByRole("button", { name: "Dismiss" }).click();
    await expect(alertRows).toHaveCount(Math.max(0, countBeforeDismiss - 1));
  });
});
