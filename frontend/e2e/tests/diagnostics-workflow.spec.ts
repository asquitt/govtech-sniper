import { test, expect } from "../fixtures/auth";

test.describe("Diagnostics Workflow", () => {
  test("connects websocket probe and receives task status", async ({
    authenticatedPage: page,
  }) => {
    await page.goto("/diagnostics");

    await expect(page.getByRole("heading", { name: "Diagnostics" })).toBeVisible();
    await expect(page.getByText("WebSocket Task Feed")).toBeVisible();

    await expect(
      page.locator("body").getByText("Connection status").locator("..")
    ).toContainText(/connected|connecting/i);

    await expect(page.locator("body")).toContainText("Last message");
    await expect(page.locator("body")).toContainText("task_status");
    await expect(page.locator("body")).toContainText("Task status");
    await expect(page.locator("body")).toContainText("Collaborative Probe");

    await page.getByRole("button", { name: "Join Document" }).click();
    await expect(page.locator("body")).toContainText("Presence Users");

    await page.getByRole("button", { name: "Lock Section", exact: true }).click();
    await expect(page.locator("body")).toContainText(/locks|lock_acquired/i);

    await page.getByRole("button", { name: "Send Cursor" }).click();
    await expect(page.locator("body")).toContainText("Cursor Telemetry");

    await page.getByLabel("Event filter").selectOption("presence_update");
    await expect(page.locator("body")).toContainText("Recent Events");

    await expect(page.getByTestId("telemetry-task-latency")).toBeVisible();
    await expect(page.getByTestId("telemetry-reconnect-count")).toBeVisible();
    await expect(page.getByTestId("telemetry-throughput")).toBeVisible();

    await page.getByLabel("Min active connection threshold").fill("2");
    await page.getByRole("button", { name: "Evaluate Alerts" }).click();
    await expect(page.getByTestId("diagnostics-alert-count")).toBeVisible();
    await expect(page.getByTestId("diagnostics-alert-active_connections_low")).toBeVisible();

    const telemetryExportPromise = page.waitForResponse((response) => {
      return (
        response.url().includes("/ws/diagnostics/export") &&
        response.request().method() === "GET" &&
        response.status() === 200
      );
    });
    await page.getByTestId("diagnostics-export-telemetry").click();
    const telemetryExportResponse = await telemetryExportPromise;
    expect(await telemetryExportResponse.headerValue("content-type")).toContain("text/csv");
  });
});
