import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: any): Promise<string> {
  const token = await page.evaluate(() => localStorage.getItem("rfp_sniper_access_token"));
  expect(token).toBeTruthy();
  return token as string;
}

test.describe("Workflow Rules Execution", () => {
  test("creates a rule and records execution after capture stage change", async ({
    authenticatedPage: page,
  }) => {
    const token = await getAccessToken(page);
    const nonce = Date.now();

    await page.goto("/settings/workflows");
    await page.getByRole("button", { name: "Add Rule" }).click();

    await page.getByPlaceholder("Rule name").fill(`E2E Stage Rule ${nonce}`);
    await page
      .locator("select")
      .first()
      .selectOption("stage_changed");
    await page.getByPlaceholder("Field (e.g. score)").fill("stage");
    await page.getByPlaceholder("Value").first().fill("proposal");
    await page.getByRole("button", { name: "Create Rule" }).click();

    await expect(page.getByText(`E2E Stage Rule ${nonce}`)).toBeVisible({ timeout: 15_000 });

    const createRfp = await page.request.post("/api/rfps", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        title: `Workflow Trigger ${nonce}`,
        solicitation_number: `E2E-WORKFLOW-${nonce}`,
        agency: "Department of Energy",
        naics_code: "541512",
      },
    });
    expect(createRfp.ok()).toBeTruthy();
    const rfp = await createRfp.json();

    const createPlan = await page.request.post("/api/capture/plans", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        rfp_id: rfp.id,
        stage: "qualified",
        bid_decision: "pending",
        win_probability: 62,
      },
    });
    expect(createPlan.ok()).toBeTruthy();
    const plan = await createPlan.json();

    const updatePlan = await page.request.patch(`/api/capture/plans/${plan.id}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        stage: "proposal",
      },
    });
    expect(updatePlan.ok()).toBeTruthy();

    await page.reload();
    await expect(page.getByText("Recent Executions")).toBeVisible();
    await expect(page.getByText(`capture_plan #${plan.id}`)).toBeVisible({ timeout: 15_000 });
  });
});
