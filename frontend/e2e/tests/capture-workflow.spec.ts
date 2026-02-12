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

test.describe("Capture Workflow", () => {
  test("creates capture plan, gate review, partner link, and competitor", async ({
    authenticatedPage: page,
  }) => {
    const rfp = await createRfp(page, "E2E Capture");
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
  });
});
