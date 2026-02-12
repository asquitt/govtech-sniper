import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: Parameters<typeof test>[0]["authenticatedPage"]) {
  const token = await page.evaluate(() =>
    localStorage.getItem("rfp_sniper_access_token")
  );
  expect(token).toBeTruthy();
  return token as string;
}

test.describe("Word Add-in Office Host Harness", () => {
  test("runs taskpane sync flow with injected Office host runtime", async ({
    authenticatedPage: page,
  }) => {
    const token = await getAccessToken(page);
    const nonce = Date.now();

    const createRfp = await page.request.post("/api/rfps", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        title: `Office Host RFP ${nonce}`,
        solicitation_number: `OFFICE-HOST-${nonce}`,
        agency: "Office Host Agency",
      },
    });
    expect(createRfp.ok()).toBeTruthy();
    const rfp = await createRfp.json();

    const createProposal = await page.request.post("/api/draft/proposals", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        rfp_id: rfp.id,
        title: `Office Host Proposal ${nonce}`,
      },
    });
    expect(createProposal.ok()).toBeTruthy();
    const proposal = await createProposal.json();

    const createSection = await page.request.post(
      `/api/draft/proposals/${proposal.id}/sections`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          title: "Executive Summary",
          section_number: "1.0",
          requirement_id: `OFFICE-${nonce}`,
          requirement_text: "Describe mission fit.",
          display_order: 1,
        },
      }
    );
    expect(createSection.ok()).toBeTruthy();

    await page.addInitScript(() => {
      const state = {
        selectedText: "Mock Office selected text",
      };
      (window as any).Office = {
        onReady: (callback?: (info: { host: string }) => void) => {
          const info = { host: "Word" };
          if (callback) {
            callback(info);
          }
          return Promise.resolve(info);
        },
      };
      (window as any).Word = {
        run: async (callback: (ctx: any) => Promise<any>) => {
          const selection = {
            text: state.selectedText,
            load: () => undefined,
            insertText: (text: string) => {
              state.selectedText = text;
            },
            insertHtml: (html: string) => {
              state.selectedText = html;
            },
          };
          const body = {
            insertParagraph: () => ({ style: "Heading 2" }),
            insertHtml: (html: string) => {
              state.selectedText = html;
            },
            search: () => ({ items: [], load: () => undefined }),
            paragraphs: { items: [], load: () => undefined },
          };
          const context = {
            document: {
              body,
              getSelection: () => selection,
            },
            sync: async () => undefined,
          };
          return callback(context);
        },
      };
    });

    await page.goto("/word-addin/taskpane");
    await expect(
      page.getByText("Running outside Word. Open this page inside Microsoft Word")
    ).toHaveCount(0);

    await expect(page.getByText(`Office Host Proposal ${nonce}`)).toBeVisible({
      timeout: 15_000,
    });
    await page.getByText("Executive Summary").click();
    await page.getByRole("button", { name: "Sync" }).click();

    await page.getByRole("button", { name: "Pull into Word" }).click();
    await expect(page.getByText(/Inserted "Executive Summary"/)).toBeVisible({
      timeout: 15_000,
    });

    await page.getByRole("button", { name: "Push from Word" }).click();
    await expect(page.getByText(/Pushed \d+ chars to section\./)).toBeVisible({
      timeout: 15_000,
    });
  });
});
