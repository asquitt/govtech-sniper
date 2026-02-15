import { test, expect } from "../fixtures/auth";

test.describe("Collaboration Workflow", () => {
  test("creates workspaces, applies contract-feed preset, and validates multi-workspace partner portal flow", async ({
    authenticatedPage: page,
    browser,
  }) => {
    const workspaceName = `Workspace A ${Date.now()}`;
    const secondaryWorkspaceName = `Workspace B ${Date.now()}`;
    const inviteEmail = `partner-${Date.now()}@example.com`;
    const invitePassword = "InvitePass1!";

    await page.goto("/collaboration");

    const createWorkspace = async (name: string, description: string) => {
      await page.getByRole("button", { name: "New Workspace" }).click();
      await page.getByPlaceholder("Workspace name").fill(name);
      await page.getByPlaceholder("Description (optional)").fill(description);
      await page.getByRole("button", { name: "Create", exact: true }).click();
      const workspaceHeading = page.getByRole("heading", { name });
      try {
        await expect(workspaceHeading).toBeVisible({ timeout: 10_000 });
      } catch {
        const workspaceButton = page.getByRole("button", { name: new RegExp(name) });
        await expect(workspaceButton).toBeVisible({ timeout: 20_000 });
        await workspaceButton.click();
        await expect(workspaceHeading).toBeVisible({ timeout: 15_000 });
      }
    };

    await createWorkspace(workspaceName, "Primary E2E collaboration flow");
    await createWorkspace(secondaryWorkspaceName, "Secondary E2E collaboration flow");

    await page.getByRole("button", { name: new RegExp(workspaceName) }).click();

    await expect(page.getByRole("heading", { name: workspaceName })).toBeVisible({
      timeout: 15_000,
    });
    const openPortalLink = page.getByRole("link", { name: "Open Partner Portal" });
    await expect(openPortalLink).toBeVisible();
    const portalHref = await openPortalLink.getAttribute("href");
    expect(portalHref).toContain("/collaboration/portal/");

    await page.getByRole("button", { name: /Shared Data \(/ }).click();
    await page.getByLabel("Contract feed preset").selectOption("federal_core");
    await page.getByRole("button", { name: "Apply Preset" }).click();
    await expect(
      page
        .locator("[data-testid^='shared-item-']")
        .filter({ hasText: "SAM.gov Federal Opportunities" })
    ).toBeVisible({ timeout: 15_000 });

    await page.getByPlaceholder("partner@company.com").fill(inviteEmail);
    await page.getByRole("button", { name: "Invite" }).click();

    await page.getByRole("button", { name: /Invitations \(/ }).click();
    const invitationRow = page.locator("[data-testid^='invitation-row-']").filter({
      hasText: inviteEmail,
    });
    await expect(invitationRow).toBeVisible({ timeout: 15_000 });

    const acceptLink = invitationRow.getByRole("link", { name: "Accept Link" });
    const acceptHrefPrimary = await acceptLink.getAttribute("href");
    expect(acceptHrefPrimary).toContain("/collaboration/accept?token=");

    await page.getByRole("button", { name: new RegExp(secondaryWorkspaceName) }).click();
    await expect(page.getByRole("heading", { name: secondaryWorkspaceName })).toBeVisible({
      timeout: 15_000,
    });
    await page.getByPlaceholder("partner@company.com").fill(inviteEmail);
    await page.getByRole("button", { name: "Invite" }).click();
    await page.getByRole("button", { name: /Invitations \(/ }).click();
    const secondaryInvitationRow = page
      .locator("[data-testid^='invitation-row-']")
      .filter({ hasText: inviteEmail });
    await expect(secondaryInvitationRow).toBeVisible({ timeout: 15_000 });
    const secondaryAcceptLink = secondaryInvitationRow.getByRole("link", {
      name: "Accept Link",
    });
    const acceptHrefSecondary = await secondaryAcceptLink.getAttribute("href");
    expect(acceptHrefSecondary).toContain("/collaboration/accept?token=");

    // Avoid SQLite write-lock flakes from owner-page background polling while collaborator accepts.
    await page.goto("about:blank");

    const collaboratorContext = await browser.newContext();
    const collaboratorPage = await collaboratorContext.newPage();

    await collaboratorPage.goto("/register");
    await collaboratorPage.getByLabel("Full Name").fill("Partner User");
    await collaboratorPage.getByLabel("Email").fill(inviteEmail);
    const company = collaboratorPage.getByLabel(/Company Name/i).first();
    if (await company.count()) {
      await company.fill("Partner Co");
    }
    await collaboratorPage.getByLabel("Password", { exact: true }).fill(invitePassword);
    await collaboratorPage.getByLabel("Confirm Password").fill(invitePassword);
    await collaboratorPage.getByRole("button", { name: "Create account" }).click();
    await collaboratorPage.waitForURL("**/opportunities", { timeout: 15_000 });

    await collaboratorPage.goto(acceptHrefPrimary!);
    await expect(collaboratorPage.getByText("Invitation accepted")).toBeVisible({
      timeout: 15_000,
    });

    await collaboratorPage.getByRole("link", { name: "Go to Workspace" }).click();
    await expect(collaboratorPage).toHaveURL(/\/collaboration\?workspace=\d+$/);
    await expect(collaboratorPage.getByRole("heading", { name: "Collaboration" })).toBeVisible({
      timeout: 15_000,
    });

    await collaboratorPage.goto(acceptHrefSecondary!);
    await expect(collaboratorPage.getByText("Invitation accepted")).toBeVisible({
      timeout: 15_000,
    });

    await collaboratorContext.close();

    await page.goto("/collaboration");
    await page.getByRole("button", { name: new RegExp(workspaceName) }).click();
    await expect(page.getByRole("heading", { name: workspaceName })).toBeVisible({
      timeout: 15_000,
    });
    await page.getByRole("button", { name: /Shared Data \(/ }).click();
    await page.getByLabel("Shared data type").selectOption("rfp_summary");
    await page.getByLabel("Shared entity id").fill("777");
    await page.getByLabel("Visible To").selectOption({ index: 1 });
    await page.getByLabel("Require approval").check();
    await page.getByRole("button", { name: "Share", exact: true }).click();
    const pendingRow = page
      .locator("[data-testid^='shared-item-']")
      .filter({ hasText: "Entity #777" });
    await expect(pendingRow).toBeVisible({ timeout: 15_000 });
    await expect(pendingRow.getByText("pending", { exact: true })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByTestId("governance-pending-count")).toHaveText("1", {
      timeout: 15_000,
    });
    await expect(page.getByTestId("governance-scoped-count")).toHaveText("1", {
      timeout: 15_000,
    });
    await expect(page.getByTestId("governance-anomaly-pending_approvals")).toBeVisible({
      timeout: 15_000,
    });
    const initialDigestPreview = page.getByTestId("compliance-digest-preview");
    if (await initialDigestPreview.count()) {
      await expect(initialDigestPreview).toContainText("pending approvals", {
        timeout: 15_000,
      });
    }
    await page.getByLabel("Digest anomalies only").check();
    await page.getByLabel("Digest recipients").selectOption("viewer");
    const digestScheduleResponsePromise = page.waitForResponse((response) => {
      return (
        response.url().includes("/compliance-digest-schedule") &&
        response.request().method() === "PATCH" &&
        response.status() === 200
      );
    });
    await page.getByRole("button", { name: "Save Schedule" }).click();
    const digestScheduleResponse = await digestScheduleResponsePromise;
    const digestSchedulePayload = await digestScheduleResponse.json();
    expect(digestSchedulePayload.recipient_role).toBe("viewer");
    await expect(page.getByTestId("compliance-digest-preview")).toContainText(
      "recipients: 1 (viewer)",
      { timeout: 15_000 }
    );

    const digestSendResponsePromise = page.waitForResponse((response) => {
      return (
        response.url().includes("/compliance-digest-send") &&
        response.request().method() === "POST" &&
        response.status() === 200
      );
    });
    await page.getByRole("button", { name: "Send Now" }).click();
    const digestSendResponse = await digestSendResponsePromise;
    const digestSendPayload = await digestSendResponse.json();
    expect(digestSendPayload.recipient_role).toBe("viewer");
    expect(digestSendPayload.recipient_count).toBe(1);
    await expect(page.getByTestId("compliance-digest-delivery-summary")).toContainText(
      "Delivery attempts: 1",
      { timeout: 15_000 }
    );
    await expect(page.getByTestId("compliance-digest-delivery-list")).toContainText("success", {
      timeout: 15_000,
    });

    await page.goto(portalHref!);
    await expect(page.getByRole("heading", { name: "Partner Portal" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText("Entity #777")).toHaveCount(0);

    await page.goto("/collaboration");
    await page.getByRole("button", { name: new RegExp(workspaceName) }).click();
    await page.getByRole("button", { name: /Shared Data \(/ }).click();
    const approvalRow = page
      .locator("[data-testid^='shared-item-']")
      .filter({ hasText: "Entity #777" });
    await approvalRow.getByRole("button", { name: "Approve" }).click();
    await expect(approvalRow.getByText("approved", { exact: true })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByTestId("governance-pending-count")).toHaveText("0", {
      timeout: 15_000,
    });
    await expect(page.getByTestId("governance-sla-percent")).toHaveText(/^\d+(\.\d+)?%$/, {
      timeout: 15_000,
    });
    await expect(page.getByTestId("governance-overdue-pending-count")).toHaveText(/^\d+$/, {
      timeout: 15_000,
    });

    const auditExportResponsePromise = page.waitForResponse((response) => {
      return (
        response.url().includes("/shared/audit-export") &&
        response.request().method() === "GET" &&
        response.status() === 200
      );
    });
    await page.getByTestId("export-governance-audit").click();
    const auditExportResponse = await auditExportResponsePromise;
    expect(await auditExportResponse.headerValue("content-type")).toContain("text/csv");

    await page.goto(portalHref!);
    await expect(page.getByText("Entity #777")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Shared Artifacts")).toBeVisible();
    await expect(page.getByLabel("Switch Workspace")).toBeVisible();
    await page.getByLabel("Switch Workspace").selectOption({
      label: secondaryWorkspaceName,
    });
    await expect(page).toHaveURL(/\/collaboration\/portal\/\d+$/);
    await expect(page.getByRole("heading", { name: secondaryWorkspaceName })).toBeVisible({
      timeout: 15_000,
    });
  });
});
