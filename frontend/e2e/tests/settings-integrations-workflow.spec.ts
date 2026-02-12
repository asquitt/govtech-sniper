import { test, expect } from "../fixtures/auth";

test.describe("Settings Integrations Workflow", () => {
  test("creates integration, validates config, runs sync, and captures webhook event", async ({
    authenticatedPage: page,
  }) => {
    const nonce = Date.now();
    const integrationName = `E2E SharePoint ${nonce}`;

    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();

    const addCard = page
      .locator(".border")
      .filter({ has: page.getByText("Add Integration", { exact: true }) })
      .first();
    await addCard.locator("select").first().selectOption("sharepoint");
    await addCard.getByPlaceholder("Name (optional)").fill(integrationName);
    await addCard.getByPlaceholder("Site URL").fill("https://example.sharepoint.com/sites/e2e");
    await addCard.getByPlaceholder("Tenant ID").fill("tenant-e2e");
    await addCard.getByPlaceholder("Client ID").fill("client-e2e");
    await addCard.getByPlaceholder("Client Secret").fill("secret-e2e");
    await addCard.getByRole("button", { name: "Create Integration" }).click();

    const integrationCard = page
      .locator(".rounded-md.border")
      .filter({ has: page.getByText(integrationName) })
      .first();
    await expect(integrationCard).toBeVisible({ timeout: 15_000 });

    await integrationCard.getByRole("button", { name: "Test", exact: true }).click();
    await expect(
      integrationCard.getByText("Test: ok - Integration configuration looks valid.")
    ).toBeVisible({ timeout: 15_000 });

    await integrationCard.getByRole("button", { name: "Run Sync", exact: true }).click();
    await expect(integrationCard.getByText("Last Sync: success")).toBeVisible({
      timeout: 15_000,
    });

    await integrationCard
      .getByRole("button", { name: "Send Test Webhook", exact: true })
      .click();
    await expect(integrationCard.getByText("Last Webhook: test.event")).toBeVisible({
      timeout: 15_000,
    });
  });

  test("manages enterprise webhook and secret controls from integrations sub-page", async ({
    authenticatedPage: page,
  }) => {
    const nonce = Date.now();
    const webhookName = `E2E Enterprise Hook ${nonce}`;
    const secretKey = `E2E_SECRET_${nonce}`;

    await page.goto("/settings/integrations");
    await expect(page.getByRole("heading", { name: "Integrations" })).toBeVisible();
    await expect(page.getByTestId("sharepoint-browser-card")).toBeVisible();
    await expect(page.getByText("SharePoint Browser")).toBeVisible();

    const webhookCard = page.getByTestId("webhook-controls-card");
    await webhookCard.getByLabel("Webhook name").fill(webhookName);
    await webhookCard.getByLabel("Webhook target URL").fill("https://example.com/webhooks/e2e");
    await webhookCard.getByLabel("Webhook event types").fill("rfp.created,proposal.section.updated");
    await webhookCard.getByLabel("Webhook signing secret").fill("whsec-initial");
    await webhookCard.getByRole("button", { name: "Create Webhook" }).click();

    const webhookRow = page.locator(".rounded-md.border").filter({ hasText: webhookName }).first();
    await expect(webhookRow).toBeVisible({ timeout: 15_000 });
    await webhookRow.getByRole("button", { name: "Load Deliveries" }).click();
    await webhookRow
      .getByLabel(new RegExp(`Rotate secret for ${webhookName}`))
      .fill("whsec-rotated");
    await webhookRow.getByRole("button", { name: "Rotate Secret" }).click();

    const secretsCard = page.getByTestId("secrets-controls-card");
    await secretsCard.getByLabel("Secret key").fill(secretKey);
    await secretsCard.getByLabel("Secret value").fill("value-one");
    await secretsCard.getByRole("button", { name: "Store Secret" }).click();

    const secretRow = page.getByTestId(`secret-row-${secretKey}`);
    await expect(secretRow).toBeVisible({ timeout: 15_000 });
    await secretRow.getByLabel(`Rotate value for ${secretKey}`).fill("value-two");
    await secretRow.getByRole("button", { name: "Rotate" }).click();
    await secretRow.getByRole("button", { name: "Delete" }).click();

    await webhookRow.getByRole("button", { name: "Delete" }).click();
    await expect(webhookRow).toBeHidden({ timeout: 15_000 });
  });
});
