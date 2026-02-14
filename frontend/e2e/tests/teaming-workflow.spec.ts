import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: any): Promise<string> {
  const token = await page.evaluate(() =>
    localStorage.getItem("rfp_sniper_access_token")
  );
  expect(token).toBeTruthy();
  return token as string;
}

async function registerUser(
  page: any,
  email: string,
  password: string,
  fullName: string,
): Promise<void> {
  await page.goto("/register");
  await page.getByLabel("Full Name").fill(fullName);
  await page.getByLabel("Email").fill(email);
  const company = page.getByLabel(/Company Name/i).first();
  if (await company.count()) {
    await company.fill("Receiver Partner Co");
  }
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/opportunities", { timeout: 15_000 });
}

async function createRfp(page: any, token: string) {
  const nonce = Date.now();
  const response = await page.request.post("/api/rfps", {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    data: {
      title: `Teaming Fit ${nonce}`,
      solicitation_number: `E2E-TEAM-${nonce}`,
      agency: "E2E Teaming Agency",
      posted_date: new Date().toISOString(),
    },
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  return payload.id as number;
}

test.describe("Teaming Workflow", () => {
  test("discovers public partner and sends teaming request", async ({
    authenticatedPage: page,
  }) => {
    const partnerName = `Public Partner ${Date.now()}`;
    const message = `E2E teaming request ${Date.now()}`;

    const token = await getAccessToken(page);
    const rfpId = await createRfp(page, token);
    const createPartner = await page.request.post("/api/capture/partners", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: { name: partnerName, partner_type: "sub" },
    });
    expect(createPartner.ok()).toBeTruthy();
    const partner = (await createPartner.json()) as { id: number };

    const makePublic = await page.request.patch(
      `/api/teaming/my-profile/${partner.id}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        params: {
          is_public: true,
          naics_codes: ["541512"],
          set_asides: ["8a"],
          capabilities: ["Cloud migration"],
        },
      }
    );
    expect(makePublic.ok()).toBeTruthy();

    await page.goto("/teaming");
    await page.getByRole("button", { name: "Search", exact: true }).click();
    await expect(page.getByText(partnerName)).toBeVisible({ timeout: 15_000 });

    const partnerCard = page
      .locator(".border.rounded-lg")
      .filter({ hasText: partnerName })
      .first();
    await partnerCard
      .getByRole("button", { name: "Request Teaming", exact: true })
      .click();

    await page.getByPlaceholder("Include a message (optional)").fill(message);
    await page.getByRole("button", { name: "Send Request" }).click();

    await page.getByRole("button", { name: /Sent \(/ }).click();
    const sentRow = page
      .locator(".border.rounded-lg")
      .filter({ hasText: partnerName })
      .filter({ hasText: message })
      .first();
    await expect(sentRow).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("teaming-total-sent")).toHaveText(/^\d+$/, {
      timeout: 15_000,
    });
    await expect(page.getByTestId("teaming-acceptance-rate")).toHaveText(/^\d+(\.\d+)?%$/, {
      timeout: 15_000,
    });
    await expect(page.locator("[data-testid^='partner-drilldown-']").first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText("NAICS Cohorts")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/541512:/)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Set-Aside Cohorts")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/8a:/i)).toBeVisible({ timeout: 15_000 });
    await page.getByLabel("Teaming digest include declined").check();
    await page.getByRole("button", { name: "Save Schedule" }).click();
    await page.getByRole("button", { name: "Send Digest" }).click();
    await expect(page.getByTestId("teaming-digest-preview")).toBeVisible({
      timeout: 15_000,
    });
    const auditExportPromise = page.waitForResponse((response) => {
      return (
        response.url().includes("/teaming/requests/audit-export") &&
        response.request().method() === "GET" &&
        response.status() === 200
      );
    });
    await page.getByTestId("teaming-export-audit").click();
    const auditExportResponse = await auditExportPromise;
    expect(await auditExportResponse.headerValue("content-type")).toContain("text/csv");

    await page.getByRole("button", { name: "Partner Search", exact: true }).click();
    await page.getByLabel("RFP ID").fill(String(rfpId));
    await page.getByRole("button", { name: "Analyze Fit", exact: true }).click();
    await expect(page.getByText("Gaps:")).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("[data-testid^='partner-fit-']").first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test("supports multi-user receive-and-accept teaming request flow", async ({
    authenticatedPage: senderPage,
    browser,
  }) => {
    const receiverEmail = `receiver-${Date.now()}@example.com`;
    const receiverPassword = "ReceiverPass1!";
    const receiverName = "Receiver Partner";
    const receiverPartnerName = `Receiver Public ${Date.now()}`;
    const message = `Need partner support ${Date.now()}`;

    const receiverContext = await browser.newContext();
    const receiverPage = await receiverContext.newPage();
    await registerUser(receiverPage, receiverEmail, receiverPassword, receiverName);

    const receiverToken = await getAccessToken(receiverPage);
    const createReceiverPartner = await receiverPage.request.post("/api/capture/partners", {
      headers: {
        Authorization: `Bearer ${receiverToken}`,
        "Content-Type": "application/json",
      },
      data: { name: receiverPartnerName, partner_type: "sub" },
    });
    expect(createReceiverPartner.ok()).toBeTruthy();
    const receiverPartner = (await createReceiverPartner.json()) as { id: number };

    const makeReceiverPartnerPublic = await receiverPage.request.patch(
      `/api/teaming/my-profile/${receiverPartner.id}`,
      {
        headers: {
          Authorization: `Bearer ${receiverToken}`,
        },
        params: { is_public: true },
      }
    );
    expect(makeReceiverPartnerPublic.ok()).toBeTruthy();

    await senderPage.goto("/teaming");
    await senderPage.getByPlaceholder("Company name...").fill(receiverPartnerName);
    await senderPage.getByRole("button", { name: "Search", exact: true }).click();
    await expect(senderPage.getByText(receiverPartnerName)).toBeVisible({ timeout: 15_000 });

    const senderPartnerCard = senderPage
      .locator(".border.rounded-lg")
      .filter({ hasText: receiverPartnerName })
      .first();
    await senderPartnerCard
      .getByRole("button", { name: "Request Teaming", exact: true })
      .click();
    await senderPage.getByPlaceholder("Include a message (optional)").fill(message);
    await senderPage.getByRole("button", { name: "Send Request" }).click();

    await senderPage.getByRole("button", { name: /Sent \(/ }).click();
    const senderSentRow = senderPage
      .locator(".border.rounded-lg")
      .filter({ hasText: message })
      .first();
    await expect(senderSentRow).toBeVisible({ timeout: 15_000 });
    await expect(senderSentRow.getByText("pending")).toBeVisible({ timeout: 15_000 });

    await receiverPage.goto("/teaming");
    await receiverPage.getByRole("button", { name: /Inbox \(/ }).click();
    const receiverInboxRow = receiverPage
      .locator(".border.rounded-lg")
      .filter({ hasText: message })
      .first();
    await expect(receiverInboxRow).toBeVisible({ timeout: 15_000 });
    await receiverInboxRow.getByRole("button", { name: "Accept", exact: true }).click();
    await expect(receiverInboxRow.getByText("accepted")).toBeVisible({ timeout: 15_000 });
    await expect(receiverInboxRow.getByText("Updated:")).toBeVisible({ timeout: 15_000 });

    await senderPage.goto("/teaming");
    await senderPage.getByRole("button", { name: /Sent \(/ }).click();
    const senderAcceptedRow = senderPage
      .locator(".border.rounded-lg")
      .filter({ hasText: message })
      .first();
    await expect(senderAcceptedRow.getByText("accepted")).toBeVisible({ timeout: 15_000 });
    await expect(senderAcceptedRow.getByText("Updated:")).toBeVisible({
      timeout: 15_000,
    });

    await receiverContext.close();
  });
});
