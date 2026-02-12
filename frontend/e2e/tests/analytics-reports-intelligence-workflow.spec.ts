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
  agency: string
) {
  const token = await getAccessToken(page);
  const response = await page.request.post("/api/rfps", {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    data: {
      title,
      solicitation_number: `E2E-AN-${Date.now()}`,
      agency,
      naics_code: "541512",
      estimated_value: 1_400_000,
      posted_date: new Date().toISOString(),
      response_deadline: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
    },
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  return payload.id as number;
}

async function createCapturePlan(
  page: Parameters<typeof test>[0]["authenticatedPage"],
  rfpId: number,
  stage: "won" | "lost" | "pursuit",
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
      stage,
      bid_decision: stage === "lost" ? "no_bid" : "bid",
      win_probability: winProbability,
    },
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  return payload.id as number;
}

test.describe("Analytics, Reports, and Intelligence Workflow", () => {
  test("loads analytics with export and completes reports workflow", async ({
    authenticatedPage: page,
  }) => {
    const nonce = Date.now();
    const wonRfp = await createRfp(page, `Won Analytics RFP ${nonce}`, "E2E Analytics Agency");
    const lostRfp = await createRfp(page, `Lost Analytics RFP ${nonce}`, "E2E Analytics Agency");
    await createCapturePlan(page, wonRfp, "won", 80);
    await createCapturePlan(page, lostRfp, "lost", 15);

    await page.goto("/analytics");
    await expect(page.getByRole("heading", { name: "Analytics" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Win Rate", exact: true })).toBeVisible();

    const analyticsDownload = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export CSV" }).click();
    const analyticsExport = await analyticsDownload;
    await expect(analyticsExport.suggestedFilename()).toContain("_export.csv");

    await page.goto("/reports");
    await expect(page.getByRole("heading", { name: "Reports" })).toBeVisible();

    await page.getByRole("button", { name: "New Report" }).click();
    await page.getByPlaceholder("e.g. Monthly Pipeline Summary").fill(`Revenue Report ${nonce}`);
    await page.locator("form select").first().selectOption("revenue");
    await page.getByRole("button", { name: "Create" }).click();

    const reportCard = page
      .locator(".rounded-xl.border")
      .filter({ has: page.getByText(`Revenue Report ${nonce}`) })
      .first();
    await expect(reportCard).toBeVisible({ timeout: 15_000 });

    await reportCard.locator("button[title='Generate']").click();
    await expect(reportCard.getByText("row", { exact: false })).toBeVisible();

    const scheduleSelect = reportCard.locator("select");
    await scheduleSelect.selectOption("weekly");
    await expect(scheduleSelect).toHaveValue("weekly");

    const reportDownload = page.waitForEvent("download");
    await reportCard.locator("button[title='Export CSV']").click();
    const reportExport = await reportDownload;
    await expect(reportExport.suggestedFilename()).toContain("revenue_report");
  });

  test("loads intelligence dashboard with seeded win/loss and pipeline data", async ({
    authenticatedPage: page,
  }) => {
    const nonce = Date.now();
    const wonRfp = await createRfp(
      page,
      `Intelligence Won ${nonce}`,
      "E2E Intelligence Agency"
    );
    const activeRfp = await createRfp(
      page,
      `Intelligence Active ${nonce}`,
      "E2E Intelligence Agency"
    );
    await createCapturePlan(page, wonRfp, "won", 88);
    await createCapturePlan(page, activeRfp, "pursuit", 62);

    await page.goto("/intelligence");
    await expect(page.getByRole("heading", { name: "Intelligence" })).toBeVisible();
    await expect(page.getByText("Win/Loss Analysis", { exact: true })).toBeVisible();
    await expect(
      page.locator("p").filter({ hasText: /^Weighted Pipeline$/ }).first()
    ).toBeVisible();
    await expect(page.getByText("By Agency", { exact: true })).toBeVisible();
  });
});
