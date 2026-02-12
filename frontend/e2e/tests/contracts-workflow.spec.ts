import { test, expect } from "../fixtures/auth";

test.describe("Contracts Workflow", () => {
  test("creates hierarchical contracts plus modifications, CLINs, CPARS, and status report", async ({
    authenticatedPage: page,
  }) => {
    const nonce = Date.now();
    const parentContractNumber = `E2E-CON-${nonce}`;
    const parentContractTitle = `E2E Parent Contract ${nonce}`;
    const childContractNumber = `E2E-CON-${nonce}-TO1`;
    const childContractTitle = `E2E Task Order ${nonce}`;
    const deliverableTitle = `Deliverable ${nonce}`;
    const taskTitle = `Task ${nonce}`;
    const modificationNumber = `P${String(nonce).slice(-4)}`;
    const clinNumber = `CL${String(nonce).slice(-4)}`;
    const cparsRating = "Excellent";
    const reportSummary = `Summary ${nonce}`;

    await page.goto("/contracts");

    const newContractCard = page
      .locator(".border")
      .filter({ has: page.getByText("New Contract", { exact: true }) })
      .first();
    await newContractCard.getByPlaceholder("Contract #").fill(parentContractNumber);
    await newContractCard.getByPlaceholder("Title").fill(parentContractTitle);
    await newContractCard.getByPlaceholder("Agency").fill("E2E Agency");
    await newContractCard.getByLabel("Contract type").selectOption("prime");
    await newContractCard.getByRole("button", { name: "Create Contract" }).click();

    await expect(
      page.getByRole("button", { name: new RegExp(parentContractTitle) }).first()
    ).toBeVisible({ timeout: 15_000 });

    await newContractCard.getByPlaceholder("Contract #").fill(childContractNumber);
    await newContractCard.getByPlaceholder("Title").fill(childContractTitle);
    await newContractCard.getByPlaceholder("Agency").fill("E2E Agency");
    await newContractCard.getByLabel("Contract type").selectOption("task_order");
    await newContractCard
      .getByLabel("Parent contract")
      .selectOption({ label: parentContractNumber });
    await newContractCard.getByRole("button", { name: "Create Contract" }).click();

    const childContractButton = page
      .getByRole("button", { name: new RegExp(childContractTitle) })
      .first();
    await expect(childContractButton).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(`Parent: ${parentContractNumber}`)).toBeVisible();
    await childContractButton.click();
    await expect(page.getByText("Hierarchy")).toBeVisible();
    await expect(page.getByText(`${parentContractNumber} - ${parentContractTitle}`)).toBeVisible();

    await page.getByPlaceholder("Deliverable title").fill(deliverableTitle);
    await page.getByRole("button", { name: "Add Deliverable" }).click();
    await expect(page.getByText(deliverableTitle)).toBeVisible();

    await page.getByPlaceholder("Task title").fill(taskTitle);
    await page.getByRole("button", { name: "Add Task" }).click();
    await expect(page.getByText(taskTitle)).toBeVisible();

    await page.getByPlaceholder("Mod #").fill(modificationNumber);
    await page.getByPlaceholder("Modification type").fill("funding");
    await page.getByLabel("Modification effective date").fill("2026-02-10");
    await page.getByPlaceholder("Value change").fill("250000");
    await page.getByPlaceholder("Modification description").fill("Funding increase");
    await page.getByRole("button", { name: "Add Mod" }).click();
    await expect(page.getByText(modificationNumber)).toBeVisible();

    await page.getByPlaceholder("CLIN #").fill(clinNumber);
    await page.getByPlaceholder("CLIN description").fill("Engineering support");
    await page.getByPlaceholder("CLIN type").fill("t_and_m");
    await page.getByPlaceholder("Qty").first().fill("3");
    await page.getByPlaceholder("Unit price").fill("1200");
    await page.getByPlaceholder("Funded").fill("2400");
    await page.getByRole("button", { name: "Add CLIN" }).click();
    await expect(page.getByText(clinNumber)).toBeVisible();
    await expect(page.getByText("Qty: 3")).toBeVisible();

    await page.getByRole("button", { name: "Edit Quantity/Funded" }).click();
    await page.getByPlaceholder("Qty").nth(1).fill("4");
    await page.getByPlaceholder("Funded amount").fill("3600");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Qty: 4")).toBeVisible();

    await page.getByPlaceholder("Rating").fill(cparsRating);
    await page.getByPlaceholder("Notes").first().fill("CPARS notes");
    await page.getByRole("button", { name: "Add Review" }).click();
    await expect(page.getByText(cparsRating)).toBeVisible();

    await page
      .getByPlaceholder("Period start (YYYY-MM-DD)")
      .fill("2026-02-01");
    await page.getByPlaceholder("Period end (YYYY-MM-DD)").fill("2026-02-28");
    await page.getByPlaceholder("Summary").fill(reportSummary);
    await page.getByPlaceholder("Risks").fill("None");
    await page.getByPlaceholder("Next steps").fill("Continue execution");
    await page.getByRole("button", { name: "Add Status Report" }).click();

    await expect(page.getByText(reportSummary)).toBeVisible();
  });
});
