import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: Parameters<typeof test>[0]["authenticatedPage"]) {
  const token = await page.evaluate(() =>
    localStorage.getItem("rfp_sniper_access_token")
  );
  expect(token).toBeTruthy();
  return token as string;
}

test.describe("Proposal Editor Workflow", () => {
  test("runs word session sync, section locks, inline review visibility, and graphics insertion", async ({
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
        title: `E2E Proposal Editor ${nonce}`,
        solicitation_number: `E2E-EDIT-${nonce}`,
        agency: "E2E Agency",
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
        title: `E2E Proposal Workspace ${nonce}`,
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
          title: "Technical Approach",
          section_number: "1.0",
          requirement_id: `REQ-${nonce}`,
          requirement_text: "Describe implementation approach.",
          display_order: 1,
        },
      }
    );
    expect(createSection.ok()).toBeTruthy();
    const section = await createSection.json();

    const seedSectionContent = await page.request.patch(
      `/api/draft/sections/${section.id}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          final_content: "Initial technical approach content for rewrite testing.",
        },
      }
    );
    expect(seedSectionContent.ok()).toBeTruthy();

    const createReview = await page.request.post(
      `/api/reviews/proposals/${proposal.id}/reviews`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          review_type: "red",
        },
      }
    );
    expect(createReview.ok()).toBeTruthy();
    const review = await createReview.json();

    const addInlineComment = await page.request.post(
      `/api/reviews/${review.id}/comments`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          section_id: section.id,
          comment_text: `Inline review feedback ${nonce}`,
          severity: "major",
          is_inline: true,
        },
      }
    );
    expect(addInlineComment.ok()).toBeTruthy();

    await page.goto(`/proposals/${proposal.id}`);
    await expect(page.getByText("Word Assistant")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Collaboration Context")).toBeVisible({ timeout: 15_000 });

    await page.getByRole("button", { name: "Rewrite" }).click();
    await page.getByRole("button", { name: "professional" }).click();
    await expect(page.getByTestId("ai-suggestions-toolbar")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: "Accept All" })).toBeVisible({
      timeout: 15_000,
    });

    await page.getByRole("button", { name: "SharePoint Export" }).click();
    await expect(page.getByRole("heading", { name: "Export to SharePoint" })).toBeVisible({
      timeout: 15_000,
    });
    await page.getByRole("button", { name: "Close" }).click();

    await page.getByPlaceholder("Document name").fill(`workspace-${nonce}.docx`);
    await page.getByRole("button", { name: "Create Word Session" }).click();
    await expect(page.getByText(`workspace-${nonce}.docx`)).toBeVisible({ timeout: 15_000 });

    const wordSessionCard = page
      .locator(".border.border-border.rounded-md")
      .filter({ hasText: `workspace-${nonce}.docx` })
      .first();
    await wordSessionCard.getByRole("button", { name: "Sync" }).click();
    await wordSessionCard.getByRole("button", { name: "History" }).click();
    await expect(wordSessionCard.getByText("Events: 1")).toBeVisible({ timeout: 15_000 });

    await expect(page.getByText(`Inline review feedback ${nonce}`)).toBeVisible();

    await page.getByPlaceholder("Graphic title").fill(`Timeline ${nonce}`);
    await page
      .getByPlaceholder("Description or layout guidance")
      .fill("Show planning, execution, and transition phases.");
    await page.getByLabel("Graphic template").selectOption("timeline");
    await page.getByRole("button", { name: "Generate Graphic" }).click();
    await expect(page.getByText("Generated Mermaid")).toBeVisible({ timeout: 20_000 });
    await page.getByRole("button", { name: "Insert into Section" }).click();

    await expect
      .poll(
        async () => {
          const sectionResponse = await page.request.get(`/api/draft/sections/${section.id}`, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          if (!sectionResponse.ok()) return null;
          const sectionPayload = await sectionResponse.json();
          return sectionPayload.final_content as string | null;
        },
        { timeout: 20_000 }
      )
      .toContain("language-mermaid");

    await page.getByRole("button", { name: "Click to edit" }).click();
    await expect(page.getByRole("button", { name: "Editing (click to release)" })).toBeVisible({
      timeout: 15_000,
    });
  });
});
