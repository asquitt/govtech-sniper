import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: Parameters<typeof test>[0]["authenticatedPage"]) {
  const token = await page.evaluate(() =>
    localStorage.getItem("rfp_sniper_access_token")
  );
  expect(token).toBeTruthy();
  return token as string;
}

test.describe("Admin Organization Workflow", () => {
  test("supports first-run organization bootstrap and capability health visibility", async ({
    authenticatedPage: page,
    browser,
  }) => {
    test.setTimeout(90_000);
    await page.goto("/admin");
    await expect(page.getByRole("heading", { name: "Admin Console" })).toBeVisible();

    await Promise.race([
      page
        .getByText("Set up your organization")
        .waitFor({ state: "visible", timeout: 20_000 })
        .catch(() => null),
      page
        .getByText("Capability Health")
        .waitFor({ state: "visible", timeout: 20_000 })
        .catch(() => null),
    ]);

    const bootstrapHeading = page.getByText("Set up your organization");
    if (await bootstrapHeading.isVisible()) {
      const nonce = Date.now();
      await page.getByLabel("Organization name").fill(`E2E Org ${nonce}`);
      await page.getByLabel("Organization slug").fill(`e2e-org-${nonce}`);
      await page.getByLabel("Domain (optional)").fill("e2e-org.example.com");
      await page
        .getByLabel("Billing email (optional)")
        .fill(`billing-${nonce}@example.com`);
      await page.getByRole("button", { name: "Create Organization" }).click();
    }

    await expect(page.getByText("Capability Health")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("Enterprise Controls")).toBeVisible({ timeout: 30_000 });

    const token = await getAccessToken(page);
    const nonce = Date.now();

    const createWebhook = await page.request.post("/api/webhooks", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        name: `E2E Webhook ${nonce}`,
        target_url: "https://example.com/e2e-webhook",
        event_types: ["rfp.created"],
        is_active: true,
      },
    });
    expect(createWebhook.ok()).toBeTruthy();

    const createSecret = await page.request.post("/api/secrets", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        key: `e2e_secret_${nonce}`,
        value: "super-secret-value",
      },
    });
    expect(createSecret.ok()).toBeTruthy();

    await page.reload();
    await expect(page.getByText("Capability Health")).toBeVisible({ timeout: 30_000 });

    const bodyText = await page.locator("body").innerText();
    const controlCounts = bodyText.match(/(\d+)\swebhooks,\s(\d+)\ssecrets/);
    expect(controlCounts).toBeTruthy();
    expect(Number(controlCounts?.[1] ?? 0)).toBeGreaterThan(0);
    expect(Number(controlCounts?.[2] ?? 0)).toBeGreaterThan(0);

    const scimIndicatorVisible =
      (await page.getByText("SCIM configured").isVisible()) ||
      (await page.getByText("SCIM not configured").isVisible());
    expect(scimIndicatorVisible).toBeTruthy();

    const inviteEmail = `org-invite-${Date.now()}@example.com`;
    const invitePassword = "InvitePass1!";
    await page.getByLabel("Invite member email").fill(inviteEmail);
    await page.getByLabel("Invite role").selectOption("member");
    await page.getByRole("button", { name: "Invite" }).click();
    const inviteRow = page
      .locator("[data-testid^='org-invitation-']")
      .filter({ hasText: inviteEmail })
      .first();
    await expect(inviteRow).toBeVisible({ timeout: 15_000 });
    await expect(inviteRow).toContainText("Awaiting registration");

    const revokeInviteEmail = `org-invite-revoke-${Date.now()}@example.com`;
    await page.getByLabel("Invite member email").fill(revokeInviteEmail);
    await page.getByRole("button", { name: "Invite" }).click();
    const revokeInviteRow = page
      .locator("[data-testid^='org-invitation-']")
      .filter({ hasText: revokeInviteEmail })
      .first();
    await expect(revokeInviteRow).toBeVisible({ timeout: 15_000 });
    await expect(revokeInviteRow).toContainText("Awaiting registration");

    const resendResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().includes("/member-invitations/") &&
        response.url().includes("/resend")
    );
    await revokeInviteRow.getByRole("button", { name: "Resend" }).click();
    const resendResponse = await resendResponsePromise;
    expect(resendResponse.ok()).toBeTruthy();

    const revokeResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().includes("/member-invitations/") &&
        response.url().includes("/revoke")
    );
    await revokeInviteRow.getByRole("button", { name: "Revoke" }).click();
    const revokeResponse = await revokeResponsePromise;
    expect(revokeResponse.ok()).toBeTruthy();
    await expect(revokeInviteRow).toContainText("revoked", { timeout: 15_000 });

    const inviteeContext = await browser.newContext();
    const inviteePage = await inviteeContext.newPage();
    await inviteePage.goto("/register");
    await inviteePage.getByLabel("Full Name").fill("Invited Admin User");
    await inviteePage.getByLabel("Email").fill(inviteEmail);
    const company = inviteePage.getByLabel(/Company Name/i).first();
    if (await company.count()) {
      await company.fill("Invited Co");
    }
    await inviteePage.getByLabel("Password", { exact: true }).fill(invitePassword);
    await inviteePage.getByLabel("Confirm Password").fill(invitePassword);
    await inviteePage.getByRole("button", { name: "Create account" }).click();
    await inviteePage.waitForURL("**/opportunities", { timeout: 15_000 });
    await inviteeContext.close();

    await page.reload();
    const readyInviteRow = page
      .locator("[data-testid^='org-invitation-']")
      .filter({ hasText: inviteEmail })
      .first();
    await expect(readyInviteRow).toContainText("Registered", { timeout: 15_000 });
    const activateResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().includes("/member-invitations/") &&
        response.url().includes("/activate")
    );
    await readyInviteRow.getByRole("button", { name: "Activate" }).click();
    const activateResponse = await activateResponsePromise;
    expect(activateResponse.ok()).toBeTruthy();
    const activatePayload = (await activateResponse.json()) as {
      status?: string;
    };
    expect((activatePayload.status ?? "").toLowerCase()).toBe("activated");
  });
});
