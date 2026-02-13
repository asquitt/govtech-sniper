import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: Parameters<typeof test>[0]["authenticatedPage"]) {
  const token = await page.evaluate(() =>
    localStorage.getItem("rfp_sniper_access_token")
  );
  expect(token).toBeTruthy();
  return token as string;
}

test.describe("Proposal Generation Workflow", () => {
  test("creates proposal, generates sections from matrix, and generates content", async ({
    authenticatedPage: page,
  }) => {
    test.slow(); // This test involves Celery tasks
    const token = await getAccessToken(page);
    const nonce = Date.now();

    // 1. Create RFP
    const rfpResponse = await page.request.post("/api/rfps", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        title: `E2E Generation Test ${nonce}`,
        solicitation_number: `E2E-GEN-${nonce}`,
        agency: "E2E Gen Agency",
        description: "Cloud infrastructure modernization and AI/ML services.",
      },
    });
    expect(rfpResponse.ok()).toBeTruthy();
    const rfp = await rfpResponse.json();

    // 2. Create compliance matrix requirements (endpoint accepts single requirement)
    const req1Response = await page.request.post(
      `/api/analyze/${rfp.id}/matrix`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          section: "L.3.1",
          requirement_text: "Describe your technical approach to cloud migration.",
          importance: "mandatory",
          category: "Technical",
        },
      }
    );
    expect(req1Response.ok()).toBeTruthy();

    await page.request.post(`/api/analyze/${rfp.id}/matrix`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        section: "L.3.2",
        requirement_text: "Provide past performance examples.",
        importance: "evaluated",
        category: "Past Performance",
      },
    });

    // 3. Create proposal
    const proposalResponse = await page.request.post("/api/draft/proposals", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        rfp_id: rfp.id,
        title: `E2E Proposal ${nonce}`,
      },
    });
    expect(proposalResponse.ok()).toBeTruthy();
    const proposal = await proposalResponse.json();

    // 4. Generate sections from compliance matrix
    const genMatrixResponse = await page.request.post(
      `/api/draft/proposals/${proposal.id}/generate-from-matrix`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      }
    );
    expect(genMatrixResponse.ok()).toBeTruthy();
    const matrixResult = await genMatrixResponse.json();
    expect(matrixResult.sections_created).toBeGreaterThanOrEqual(1);

    // 5. Verify sections exist
    const sectionsResponse = await page.request.get(
      `/api/draft/proposals/${proposal.id}/sections`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(sectionsResponse.ok()).toBeTruthy();
    const sections = await sectionsResponse.json();
    expect(sections.length).toBeGreaterThanOrEqual(1);

    const firstSection = sections[0];

    // 6. Generate content for first section
    const generateResponse = await page.request.post(
      `/api/draft/${firstSection.requirement_id}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: {
          requirement_id: firstSection.requirement_id,
          rfp_id: rfp.id,
          max_words: 300,
        },
      }
    );
    expect(generateResponse.ok()).toBeTruthy();
    const genResult = await generateResponse.json();
    expect(genResult.task_id).toBeTruthy();

    // 7. Poll for generation completion
    await expect
      .poll(
        async () => {
          const statusResponse = await page.request.get(
            `/api/draft/${genResult.task_id}/status`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          if (!statusResponse.ok()) return "error";
          const status = await statusResponse.json();
          return status.status as string;
        },
        { timeout: 30_000, intervals: [2_000] }
      )
      .toBe("completed");

    // 8. Verify section now has generated content
    const updatedSection = await page.request.get(
      `/api/draft/sections/${firstSection.id}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(updatedSection.ok()).toBeTruthy();
    const sectionData = await updatedSection.json();
    expect(sectionData.generated_content).toBeTruthy();

    // 9. Verify generation progress
    const progressResponse = await page.request.get(
      `/api/draft/proposals/${proposal.id}/generation-progress`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(progressResponse.ok()).toBeTruthy();
    const progress = await progressResponse.json();
    expect(progress.completed).toBeGreaterThanOrEqual(1);
    expect(progress.completion_percentage).toBeGreaterThan(0);
  });

  test("generates outline via AI and approves to create sections", async ({
    authenticatedPage: page,
  }) => {
    test.slow();
    const token = await getAccessToken(page);
    const nonce = Date.now();

    // Setup: RFP + Matrix + Proposal
    const rfpResponse = await page.request.post("/api/rfps", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        title: `E2E Outline Test ${nonce}`,
        solicitation_number: `E2E-OUT-${nonce}`,
        agency: "E2E Outline Agency",
      },
    });
    const rfp = await rfpResponse.json();

    await page.request.post(`/api/analyze/${rfp.id}/matrix`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: {
        section: "L.4",
        requirement_text: "Provide management approach.",
        importance: "mandatory",
        category: "Management",
      },
    });

    const proposalResponse = await page.request.post("/api/draft/proposals", {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: { rfp_id: rfp.id, title: `E2E Outline Proposal ${nonce}` },
    });
    const proposal = await proposalResponse.json();

    // Generate outline via AI (triggers Celery task)
    const generateOutlineResponse = await page.request.post(
      `/api/draft/proposals/${proposal.id}/generate-outline`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      }
    );
    expect(generateOutlineResponse.ok()).toBeTruthy();

    // Poll for outline to be generated
    await expect
      .poll(
        async () => {
          const outlineR = await page.request.get(
            `/api/draft/proposals/${proposal.id}/outline`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          if (!outlineR.ok()) return "pending";
          const outline = await outlineR.json();
          return outline.status as string;
        },
        { timeout: 30_000, intervals: [2_000] }
      )
      .toBe("draft");

    // Get outline and verify sections were generated
    const outlineResponse = await page.request.get(
      `/api/draft/proposals/${proposal.id}/outline`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(outlineResponse.ok()).toBeTruthy();
    const outline = await outlineResponse.json();
    expect(outline.sections.length).toBeGreaterThanOrEqual(1);
    expect(outline.status).toBe("draft");

    // Approve outline → creates proposal sections
    const approveResponse = await page.request.post(
      `/api/draft/proposals/${proposal.id}/outline/approve`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      }
    );
    expect(approveResponse.ok()).toBeTruthy();
    const approveResult = await approveResponse.json();
    expect(approveResult.sections_created).toBeGreaterThanOrEqual(1);

    // Verify sections were created
    const sectionsResponse = await page.request.get(
      `/api/draft/proposals/${proposal.id}/sections`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const sections = await sectionsResponse.json();
    expect(sections.length).toBeGreaterThanOrEqual(1);
  });
});
