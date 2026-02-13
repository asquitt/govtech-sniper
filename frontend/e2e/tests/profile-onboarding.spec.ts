import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: Parameters<typeof test>[0]["authenticatedPage"]) {
  const token = await page.evaluate(() =>
    localStorage.getItem("rfp_sniper_access_token")
  );
  expect(token).toBeTruthy();
  return token as string;
}

test.describe("Profile and Onboarding", () => {
  test("retrieves and updates user qualification profile", async ({
    authenticatedPage: page,
  }) => {
    const token = await getAccessToken(page);

    // Get initial profile (should be empty defaults)
    const getResponse = await page.request.get("/api/auth/profile", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(getResponse.ok()).toBeTruthy();
    const profile = await getResponse.json();
    expect(profile).toHaveProperty("naics_codes");
    expect(profile).toHaveProperty("clearance_level");

    // Update profile with realistic data
    const updateResponse = await page.request.put("/api/auth/profile", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        naics_codes: ["541512", "541511"],
        clearance_level: "secret",
        set_aside_types: ["8a", "WOSB"],
        preferred_states: ["VA", "MD", "DC"],
        min_contract_value: 100000,
        max_contract_value: 10000000,
        include_keywords: ["cloud", "AI", "modernization"],
        exclude_keywords: ["classified"],
      },
    });
    expect(updateResponse.ok()).toBeTruthy();

    // Verify update persisted
    const verifyResponse = await page.request.get("/api/auth/profile", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const updated = await verifyResponse.json();
    expect(updated.naics_codes).toContain("541512");
    expect(updated.clearance_level).toBe("secret");
    expect(updated.set_aside_types).toContain("8a");
    expect(updated.preferred_states).toContain("VA");
    expect(updated.min_contract_value).toBe(100000);
    expect(updated.include_keywords).toContain("cloud");
  });

  test("onboarding progress auto-detects completed steps", async ({
    authenticatedPage: page,
  }) => {
    const token = await getAccessToken(page);

    // Get onboarding progress — should have create_account completed
    const progressResponse = await page.request.get(
      "/api/onboarding/progress",
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(progressResponse.ok()).toBeTruthy();
    const progress = await progressResponse.json();

    expect(progress.steps).toBeDefined();
    expect(progress.total_steps).toBe(6);
    expect(progress.completed_count).toBeGreaterThanOrEqual(1);

    // create_account should always be complete for authenticated user
    const createAccountStep = progress.steps.find(
      (s: { id: string }) => s.id === "create_account"
    );
    expect(createAccountStep?.completed).toBe(true);
  });

  test("onboarding wizard renders when not dismissed", async ({
    authenticatedPage: page,
  }) => {
    const token = await getAccessToken(page);

    // Check if wizard is already dismissed
    const progressResponse = await page.request.get(
      "/api/onboarding/progress",
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const progress = await progressResponse.json();

    if (progress.is_dismissed) {
      test.skip(true, "Wizard already dismissed from prior test run");
      return;
    }

    await page.goto("/opportunities");

    // The onboarding wizard should be visible in sidebar
    await expect(
      page.getByText("Getting Started").first()
    ).toBeVisible({ timeout: 10_000 });

    // Should show step titles
    await expect(page.getByText("Create your account")).toBeVisible();
  });

  test("manually marks onboarding step and dismisses wizard", async ({
    authenticatedPage: page,
  }) => {
    const token = await getAccessToken(page);

    // Mark export step as complete
    const markResponse = await page.request.post(
      "/api/onboarding/steps/export_proposal/complete",
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      }
    );
    expect(markResponse.ok()).toBeTruthy();

    // Verify step is now completed
    const progressResponse = await page.request.get(
      "/api/onboarding/progress",
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const progress = await progressResponse.json();
    const exportStep = progress.steps.find(
      (s: { id: string }) => s.id === "export_proposal"
    );
    expect(exportStep?.completed).toBe(true);

    // Dismiss the wizard
    const dismissResponse = await page.request.post(
      "/api/onboarding/dismiss",
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      }
    );
    expect(dismissResponse.ok()).toBeTruthy();
  });
});
