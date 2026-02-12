import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: any): Promise<string> {
  const token = await page.evaluate(() =>
    localStorage.getItem("rfp_sniper_access_token")
  );
  expect(token).toBeTruthy();
  return token as string;
}

test.describe("Reviews Workflow", () => {
  test("shows scheduled review on dashboard with filters", async ({
    authenticatedPage: page,
  }) => {
    const token = await getAccessToken(page);
    const nonce = Date.now();
    const proposalTitle = `E2E Review Proposal ${nonce}`;

    const createRfp = await page.request.post("/api/rfps", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        title: `E2E Review RFP ${nonce}`,
        solicitation_number: `E2E-REV-${nonce}`,
        agency: "E2E Review Agency",
        posted_date: new Date().toISOString(),
      },
    });
    expect(createRfp.ok()).toBeTruthy();
    const rfp = (await createRfp.json()) as { id: number };

    const createProposal = await page.request.post("/api/draft/proposals", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        rfp_id: rfp.id,
        title: proposalTitle,
      },
    });
    expect(createProposal.ok()).toBeTruthy();
    const proposal = (await createProposal.json()) as { id: number };

    const scheduleReview = await page.request.post(
      `/api/reviews/proposals/${proposal.id}/reviews`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          review_type: "red",
        },
      }
    );
    expect(scheduleReview.ok()).toBeTruthy();

    await page.goto("/reviews");
    await expect(page.getByText(proposalTitle)).toBeVisible({ timeout: 15_000 });

    await page.getByRole("button", { name: "RED Team" }).click();
    await page.getByRole("button", { name: "Scheduled" }).click();
    await expect(page.getByText(proposalTitle)).toBeVisible();
  });
});
