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
  titlePrefix: string
) {
  const token = await getAccessToken(page);
  const nonce = Date.now();
  const title = `${titlePrefix} ${nonce}`;
  const response = await page.request.post("/api/rfps", {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    data: {
      title,
      solicitation_number: `E2E-CAP-${nonce}`,
      agency: "E2E Capture Agency",
      posted_date: new Date().toISOString(),
    },
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  return { id: payload.id as number, title };
}

async function createHumanBidScorecard(
  page: Parameters<typeof test>[0]["authenticatedPage"],
  rfpId: number
) {
  const token = await getAccessToken(page);
  const criteria = [
    { name: "technical_capability", weight: 15, score: 80 },
    { name: "past_performance", weight: 12, score: 78 },
    { name: "price_competitiveness", weight: 10, score: 70 },
    { name: "staffing_availability", weight: 10, score: 74 },
    { name: "clearance_requirements", weight: 10, score: 82 },
    { name: "set_aside_eligibility", weight: 8, score: 79 },
    { name: "relationship_with_agency", weight: 8, score: 72 },
    { name: "competitive_landscape", weight: 7, score: 68 },
    { name: "geographic_fit", weight: 5, score: 81 },
    { name: "contract_vehicle_access", weight: 5, score: 76 },
    { name: "teaming_strength", weight: 5, score: 67 },
    { name: "proposal_timeline", weight: 5, score: 73 },
  ];
  const response = await page.request.post(`/api/capture/scorecards/${rfpId}/vote`, {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    data: {
      criteria_scores: criteria,
      overall_score: 75,
      recommendation: "bid",
      reasoning: "Baseline vote for stress-test workflow validation.",
    },
  });
  expect(response.ok()).toBeTruthy();
}

test.describe("Capture Workflow", () => {
  test("creates capture plan, gate review, partner link, competitor, and stress-test simulation", async ({
    authenticatedPage: page,
  }) => {
    const rfp = await createRfp(page, "E2E Capture");
    await createHumanBidScorecard(page, rfp.id);
    const noteText = `Gate note ${Date.now()}`;
    const partnerName = `Partner ${Date.now()}`;
    const competitorName = `Competitor ${Date.now()}`;

    await page.goto("/capture");

    const rfpRow = page.locator("div").filter({ hasText: rfp.title }).first();
    await expect(rfpRow).toBeVisible({ timeout: 15_000 });
    await rfpRow.getByRole("button", { name: "Create Capture Plan" }).click();
    await expect(rfpRow.getByText("Plan Active", { exact: true }).first()).toBeVisible();

    const gateCard = page
      .locator(".bg-card")
      .filter({ has: page.getByText("Gate Reviews", { exact: true }) })
      .first();
    await gateCard.locator("select").first().selectOption({ label: rfp.title });
    await gateCard.locator("input[placeholder='Notes']").fill(noteText);
    await gateCard.getByRole("button", { name: "Add Review" }).click();
    await expect(gateCard.getByText(noteText)).toBeVisible();

    const teamingCard = page
      .locator(".bg-card")
      .filter({ has: page.getByText("Teaming Partners", { exact: true }) })
      .first();
    await teamingCard.locator("input[placeholder='Partner name']").fill(partnerName);
    await teamingCard.getByRole("button", { name: "Add Partner" }).click();
    await teamingCard.locator("select").first().selectOption({ label: rfp.title });
    await teamingCard.locator("select").nth(1).selectOption({ label: partnerName });
    await teamingCard
      .locator("input[placeholder='Role (Subcontractor)']")
      .fill("Subcontractor");
    await teamingCard.getByRole("button", { name: "Link" }).click();
    await expect(
      teamingCard.locator("p.font-medium", { hasText: partnerName })
    ).toBeVisible();

    const competitorCard = page
      .locator(".bg-card")
      .filter({ has: page.getByText("Competitor Comparisons", { exact: true }) })
      .first();
    await competitorCard
      .locator("input[placeholder='Competitor name']")
      .fill(competitorName);
    await competitorCard.getByRole("button", { name: "Add Competitor" }).click();
    await expect(competitorCard.getByText(competitorName)).toBeVisible();

    const stressCard = page
      .locator(".bg-card")
      .filter({ has: page.getByText("Stress Test Mode", { exact: true }) })
      .first();
    await stressCard.getByRole("button", { name: "Run Scenario Simulator" }).click();
    const scenarioResultsCard = page
      .locator(".bg-card")
      .filter({ has: page.getByText("Scenario Results", { exact: true }) })
      .first();
    await expect(scenarioResultsCard).toBeVisible();
    await expect(
      scenarioResultsCard.locator("p.font-medium", { hasText: "Aggressive Incumbent Response" })
    ).toBeVisible();
    await expect(
      scenarioResultsCard.locator("p.font-medium", { hasText: "Strategic Teaming Lift" })
    ).toBeVisible();
  });
});
