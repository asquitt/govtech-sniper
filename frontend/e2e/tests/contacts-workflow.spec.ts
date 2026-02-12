import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: any): Promise<string> {
  const token = await page.evaluate(() =>
    localStorage.getItem("rfp_sniper_access_token")
  );
  expect(token).toBeTruthy();
  return token as string;
}

async function createRfpForContactExtraction(page: any, token: string): Promise<number> {
  const nonce = Date.now();
  const response = await page.request.post("/api/rfps", {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    data: {
      title: `Contacts Extract ${nonce}`,
      solicitation_number: `E2E-CONTACT-${nonce}`,
      agency: "Department of Energy",
      description: "Please direct all questions to the Contracting Officer.",
    },
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  return payload.id as number;
}

test.describe("Contacts Workflow", () => {
  test("extracts contacts and auto-links them to opportunity and agency directory", async ({
    authenticatedPage: page,
  }) => {
    const token = await getAccessToken(page);
    const rfpId = await createRfpForContactExtraction(page, token);

    await page.goto("/contacts");
    await page.getByRole("button", { name: "Extract from RFP" }).click();
    await page.getByPlaceholder("Enter RFP ID").fill(String(rfpId));
    await page.getByRole("button", { name: "Extract", exact: true }).click();

    await expect(page.getByText(/contact extracted/)).toBeVisible({ timeout: 15_000 });
    await expect(
      page.getByText(/linked automatically to this opportunity and agency directory/i)
    ).toBeVisible({ timeout: 15_000 });

    await page.getByLabel("Close extraction modal").click();

    await expect(page.locator("table").getByText("Contact extracted from document")).toBeVisible({
      timeout: 15_000,
    });

    await page.getByRole("button", { name: "Agency Directory" }).click();
    await expect(page.getByText("Department of Energy")).toBeVisible({ timeout: 15_000 });
  });
});
