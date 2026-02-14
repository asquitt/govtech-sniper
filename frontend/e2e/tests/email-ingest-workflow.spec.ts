import { expect, test } from "../fixtures/auth";

test.describe("Email Ingest Workflow", () => {
  test("configures ingest account and runs sync-now", async ({ authenticatedPage: page }) => {
    const workspaces = [
      {
        id: 7,
        owner_id: 1,
        rfp_id: null,
        name: "Capture Workspace",
        description: "Workspace for routed ingest notifications",
        member_count: 3,
        created_at: "2026-02-14T00:00:00Z",
        updated_at: "2026-02-14T00:00:00Z",
      },
    ];

    const configs: any[] = [];

    await page.route("**/api/collaboration/workspaces", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(workspaces),
      });
    });

    await page.route("**/api/email-ingest/config", async (route) => {
      const method = route.request().method();
      if (method === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(configs),
        });
        return;
      }
      if (method === "POST") {
        const payload = route.request().postDataJSON() as Record<string, unknown>;
        const created = {
          id: configs.length + 1,
          user_id: 1,
          workspace_id: payload.workspace_id ?? null,
          imap_server: payload.imap_server,
          imap_port: payload.imap_port,
          email_address: payload.email_address,
          encrypted_password: "********",
          folder: payload.folder ?? "INBOX",
          is_enabled: true,
          auto_create_rfps: payload.auto_create_rfps ?? true,
          min_rfp_confidence: payload.min_rfp_confidence ?? 0.35,
          last_checked_at: null,
          created_at: "2026-02-14T00:00:00Z",
          updated_at: "2026-02-14T00:00:00Z",
        };
        configs.push(created);
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(created),
        });
        return;
      }

      await route.fulfill({ status: 405 });
    });

    await page.route("**/api/email-ingest/history**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [], total: 0 }),
      });
    });

    await page.route("**/api/email-ingest/sync-now", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          configs_checked: 1,
          fetched: 2,
          duplicates: 0,
          poll_errors: 0,
          processed: 2,
          created_rfps: 1,
          inbox_forwarded: 1,
          process_errors: 0,
        }),
      });
    });

    await page.goto("/settings/email-ingest");

    await page.getByRole("button", { name: "Add Account" }).click();
    await page.getByLabel("IMAP Server").fill("imap.example.com");
    await page.getByLabel("IMAP Port").fill("993");
    await page.getByLabel("Email Address").fill("capture@example.com");
    await page.getByLabel("App Password").fill("secret");
    await page.getByLabel("Folder").fill("INBOX");
    await page.getByLabel("Team Workspace (Optional)").selectOption("7");
    await page.getByLabel("Minimum RFP Confidence (0-1)").fill("0.6");
    await page.getByRole("button", { name: "Save Configuration" }).click();

    await expect(page.getByText("capture@example.com")).toBeVisible({ timeout: 10_000 });

    await page.getByRole("button", { name: "Run Sync Now" }).click();
    await expect(
      page.getByText("Sync complete: fetched 2, processed 2, created 1 opportunities."),
    ).toBeVisible({ timeout: 10_000 });
  });
});
