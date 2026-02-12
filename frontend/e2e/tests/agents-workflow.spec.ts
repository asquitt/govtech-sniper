import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: any): Promise<string> {
  const token = await page.evaluate(() => localStorage.getItem("rfp_sniper_access_token"));
  expect(token).toBeTruthy();
  return token as string;
}

async function createAgentRfp(page: any, token: string): Promise<number> {
  const nonce = Date.now();
  const response = await page.request.post("/api/rfps", {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    data: {
      title: `Agents Workflow ${nonce}`,
      solicitation_number: `E2E-AGENT-${nonce}`,
      agency: "Department of Homeland Security",
      naics_code: "541512",
      description: "Need capture planning and proposal prep support.",
    },
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  return payload.id as number;
}

test.describe("Agents Workflow", () => {
  test("runs all autonomous agents for a selected opportunity", async ({
    authenticatedPage: page,
  }) => {
    const token = await getAccessToken(page);
    const rfpId = await createAgentRfp(page, token);

    await page.goto("/agents");
    await expect(page.getByRole("heading", { name: "Autonomous Agents" })).toBeVisible();

    await page.locator("select").first().selectOption(String(rfpId));

    const agentCards = [
      "Research Agent",
      "Capture Planning Agent",
      "Proposal Prep Agent",
      "Competitive Intel Agent",
    ];

    for (const title of agentCards) {
      const heading = page.getByRole("heading", { name: title });
      const card = heading.locator("xpath=ancestor::div[contains(@class,'border')][1]");
      await card.getByRole("button", { name: "Run Agent" }).click();
      await expect(card.getByText("Latest Run Summary")).toBeVisible({ timeout: 20_000 });
    }
  });
});
