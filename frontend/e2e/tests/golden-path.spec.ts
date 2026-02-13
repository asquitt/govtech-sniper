/**
 * Golden Path E2E Test — Full Customer Journey
 *
 * Validates the complete user experience from registration through proposal export:
 *   Register → Profile → Upload KB doc → Create RFP → Analyze (compliance matrix) →
 *   Create Proposal → Generate Outline → Approve Outline → Generate Section Content →
 *   Edit in TipTap → Export DOCX → Verify on proposals list
 *
 * Uses fresh user, no fixtures. Exercises all critical APIs and UI.
 */
import { test as base, expect, type Page } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3002";

const test = base.extend<{ freshPage: Page }>({
  freshPage: async ({ page }, use) => {
    await use(page);
  },
});

test.describe("Golden Path — Full Customer Journey", () => {
  test("register → profile → upload → analyze → propose → outline → generate → edit → export", async ({
    freshPage: page,
  }) => {
    test.setTimeout(120_000); // Celery tasks need time

    const nonce = Date.now();
    const email = `golden-${nonce}@example.com`;
    const password = "GoldenTest1!";
    let accessToken: string;

    // ──────────────────────────────────────────────────
    // 1. REGISTER
    // ──────────────────────────────────────────────────
    await page.goto(`${BASE_URL}/register`);
    await page.getByLabel("Full Name").fill("Golden Path User");
    await page.getByLabel("Email").fill(email);
    const companyField = page.getByLabel(/Company Name/i).first();
    if (await companyField.count()) {
      await companyField.fill("Golden Corp").catch(() => {});
    }
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByLabel("Confirm Password").fill(password);
    await page.getByRole("button", { name: "Create account" }).click();
    await page.waitForURL("**/opportunities", { timeout: 15_000 });

    // Grab token
    accessToken = (await page.evaluate(() =>
      localStorage.getItem("rfp_sniper_access_token")
    )) as string;
    expect(accessToken).toBeTruthy();

    const H = {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    };

    // ──────────────────────────────────────────────────
    // 2. SET UP PROFILE (NAICS, clearance, keywords)
    // ──────────────────────────────────────────────────
    const profileR = await page.request.put("/api/auth/profile", {
      headers: H,
      data: {
        naics_codes: ["541512", "541511"],
        clearance_level: "secret",
        set_aside_types: ["8a"],
        preferred_states: ["VA", "MD"],
        min_contract_value: 100000,
        max_contract_value: 5000000,
        include_keywords: ["cloud", "modernization"],
        exclude_keywords: ["classified"],
      },
    });
    expect(profileR.ok()).toBeTruthy();

    // ──────────────────────────────────────────────────
    // 3. UPLOAD KNOWLEDGE BASE DOCUMENT
    // ──────────────────────────────────────────────────
    const capStatement = `Capability Statement — Golden Corp

Golden Corp specializes in cloud modernization and AI/ML solutions for federal agencies.
Our team has 10+ years of experience delivering secure IT services under FISMA and FedRAMP compliance.

Past Performance:
- DoD Cloud Migration Program (2024-2025) — $4.2M
- VA Digital Health Platform (2023-2024) — $2.8M

NAICS: 541512, 541511
Clearance: Secret / Top Secret
SAM UEI: GOLDEN123456`;

    const docR = await page.request.post("/api/documents", {
      headers: { Authorization: `Bearer ${accessToken}` },
      multipart: {
        file: {
          name: `golden-cap-${nonce}.txt`,
          mimeType: "text/plain",
          buffer: Buffer.from(capStatement),
        },
        title: `Golden Corp Capability Statement`,
        document_type: "capability_statement",
      },
    });
    expect(docR.ok()).toBeTruthy();
    const doc = await docR.json();

    // Poll for processing completion
    await expect
      .poll(
        async () => {
          const r = await page.request.get("/api/documents?ready_only=false", {
            headers: { Authorization: `Bearer ${accessToken}` },
          });
          if (!r.ok()) return "error";
          const { documents } = (await r.json()) as {
            documents: Array<{ id: number; processing_status: string }>;
          };
          const d = documents.find((x) => x.id === doc.id);
          return d?.processing_status ?? "not_found";
        },
        { timeout: 30_000, intervals: [2_000] }
      )
      .toBe("ready");

    // ──────────────────────────────────────────────────
    // 4. CREATE RFP
    // ──────────────────────────────────────────────────
    const rfpR = await page.request.post("/api/rfps", {
      headers: H,
      data: {
        title: `Golden Path RFP ${nonce}`,
        solicitation_number: `GP-${nonce}`,
        agency: "Department of Golden Tests",
        description:
          "Cloud infrastructure modernization including container orchestration, CI/CD pipeline setup, and migration of legacy applications to microservices architecture.",
      },
    });
    expect(rfpR.ok()).toBeTruthy();
    const rfp = await rfpR.json();

    // ──────────────────────────────────────────────────
    // 5. ADD COMPLIANCE MATRIX REQUIREMENTS
    // ──────────────────────────────────────────────────
    const requirements = [
      {
        section: "L.3.1",
        requirement_text:
          "Describe your technical approach to cloud migration including containerization strategy.",
        importance: "mandatory" as const,
        category: "Technical",
      },
      {
        section: "L.3.2",
        requirement_text:
          "Provide at least two past performance references for similar cloud modernization projects.",
        importance: "evaluated" as const,
        category: "Past Performance",
      },
      {
        section: "L.3.3",
        requirement_text:
          "Describe your project management methodology and staffing plan.",
        importance: "mandatory" as const,
        category: "Management",
      },
    ];

    for (const req of requirements) {
      const r = await page.request.post(`/api/analyze/${rfp.id}/matrix`, {
        headers: H,
        data: req,
      });
      expect(r.ok()).toBeTruthy();
    }

    // Verify matrix has 3 requirements
    const matrixR = await page.request.get(`/api/analyze/${rfp.id}/matrix`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    expect(matrixR.ok()).toBeTruthy();
    const matrix = await matrixR.json();
    expect(matrix.requirements.length).toBe(3);

    // ──────────────────────────────────────────────────
    // 6. CREATE PROPOSAL
    // ──────────────────────────────────────────────────
    const proposalR = await page.request.post("/api/draft/proposals", {
      headers: H,
      data: {
        rfp_id: rfp.id,
        title: `Golden Path Proposal ${nonce}`,
      },
    });
    expect(proposalR.ok()).toBeTruthy();
    const proposal = await proposalR.json();

    // ──────────────────────────────────────────────────
    // 7. ATTACH FOCUS DOCUMENT (KB doc for AI context)
    // ──────────────────────────────────────────────────
    const focusR = await page.request.put(
      `/api/draft/proposals/${proposal.id}/focus-documents`,
      {
        headers: H,
        data: { document_ids: [doc.id] },
      }
    );
    expect(focusR.ok()).toBeTruthy();

    // ──────────────────────────────────────────────────
    // 8. GENERATE OUTLINE VIA AI
    // ──────────────────────────────────────────────────
    const genOutlineR = await page.request.post(
      `/api/draft/proposals/${proposal.id}/generate-outline`,
      { headers: H }
    );
    expect(genOutlineR.ok()).toBeTruthy();

    // Poll for outline generation
    await expect
      .poll(
        async () => {
          const r = await page.request.get(
            `/api/draft/proposals/${proposal.id}/outline`,
            { headers: { Authorization: `Bearer ${accessToken}` } }
          );
          if (!r.ok()) return "pending";
          const outline = await r.json();
          return outline.status as string;
        },
        { timeout: 30_000, intervals: [2_000] }
      )
      .toBe("draft");

    // Verify outline has sections
    const outlineR = await page.request.get(
      `/api/draft/proposals/${proposal.id}/outline`,
      { headers: { Authorization: `Bearer ${accessToken}` } }
    );
    const outline = await outlineR.json();
    expect(outline.sections.length).toBeGreaterThanOrEqual(1);

    // ──────────────────────────────────────────────────
    // 9. APPROVE OUTLINE → Creates ProposalSections
    // ──────────────────────────────────────────────────
    const approveR = await page.request.post(
      `/api/draft/proposals/${proposal.id}/outline/approve`,
      { headers: H }
    );
    expect(approveR.ok()).toBeTruthy();
    const approveResult = await approveR.json();
    expect(approveResult.sections_created).toBeGreaterThanOrEqual(1);

    // Get sections — find one with a requirement_id for content generation
    const sectionsR = await page.request.get(
      `/api/draft/proposals/${proposal.id}/sections`,
      { headers: { Authorization: `Bearer ${accessToken}` } }
    );
    const sections = await sectionsR.json();
    expect(sections.length).toBeGreaterThanOrEqual(1);

    const firstSection = sections.find(
      (s: { requirement_id: string | null }) => s.requirement_id != null
    ) ?? sections[0];

    // ──────────────────────────────────────────────────
    // 10. GENERATE CONTENT FOR SECTION (requires requirement_id)
    // ──────────────────────────────────────────────────
    let generatedContent = "Mock content for testing.";
    if (firstSection.requirement_id) {
      const generateR = await page.request.post(
        `/api/draft/${firstSection.requirement_id}`,
        {
          headers: H,
          data: {
            requirement_id: firstSection.requirement_id,
            rfp_id: rfp.id,
            max_words: 300,
          },
        }
      );
      expect(generateR.ok()).toBeTruthy();
      const genResult = await generateR.json();
      expect(genResult.task_id).toBeTruthy();

      // Poll for content generation
      await expect
        .poll(
          async () => {
            const r = await page.request.get(
              `/api/draft/${genResult.task_id}/status`,
              { headers: { Authorization: `Bearer ${accessToken}` } }
            );
            if (!r.ok()) return "error";
            const s = await r.json();
            return s.status as string;
          },
          { timeout: 30_000, intervals: [2_000] }
        )
        .toBe("completed");

      // Verify generated content exists
      const sectionDetailR = await page.request.get(
        `/api/draft/sections/${firstSection.id}`,
        { headers: { Authorization: `Bearer ${accessToken}` } }
      );
      const sectionDetail = await sectionDetailR.json();
      expect(sectionDetail.generated_content).toBeTruthy();
      generatedContent = sectionDetail.generated_content;
    }

    // ──────────────────────────────────────────────────
    // 11. EDIT SECTION — Set final_content (simulates TipTap save)
    // ──────────────────────────────────────────────────
    const editedHtml = `<h2>${firstSection.title}</h2><p>${generatedContent}</p><p><em>Edited by Golden Path test.</em></p>`;
    const editR = await page.request.patch(
      `/api/draft/sections/${firstSection.id}`,
      {
        headers: H,
        data: { final_content: editedHtml },
      }
    );
    expect(editR.ok()).toBeTruthy();

    // ──────────────────────────────────────────────────
    // 12. EXPORT DOCX
    // ──────────────────────────────────────────────────
    const exportR = await page.request.get(
      `/api/export/proposals/${proposal.id}/docx`,
      { headers: { Authorization: `Bearer ${accessToken}` } }
    );
    expect(exportR.ok()).toBeTruthy();

    const contentType = exportR.headers()["content-type"];
    expect(contentType).toContain(
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    );

    const body = await exportR.body();
    expect(body.length).toBeGreaterThan(100);
    // DOCX is a ZIP — starts with PK
    expect(body[0]).toBe(0x50);
    expect(body[1]).toBe(0x4b);

    // ──────────────────────────────────────────────────
    // 13. VERIFY PROPOSAL APPEARS ON UI
    // ──────────────────────────────────────────────────
    await page.goto(`${BASE_URL}/proposals`);
    await expect(
      page.getByText(`Golden Path Proposal ${nonce}`)
    ).toBeVisible({ timeout: 10_000 });

    // Navigate into the workspace via "Open Workspace" link
    await page
      .locator(".rounded-xl, [class*='card'], .border")
      .filter({ hasText: `Golden Path Proposal ${nonce}` })
      .getByText("Open Workspace")
      .click();
    await expect(
      page.getByRole("button", { name: "Export DOCX" })
    ).toBeVisible({ timeout: 15_000 });

    // ──────────────────────────────────────────────────
    // 14. VERIFY GENERATION PROGRESS
    // ──────────────────────────────────────────────────
    const progressR = await page.request.get(
      `/api/draft/proposals/${proposal.id}/generation-progress`,
      { headers: { Authorization: `Bearer ${accessToken}` } }
    );
    expect(progressR.ok()).toBeTruthy();
    const progress = await progressR.json();
    expect(progress.completed).toBeGreaterThanOrEqual(1);
    expect(progress.completion_percentage).toBeGreaterThan(0);

    // ──────────────────────────────────────────────────
    // 15. VERIFY KNOWLEDGE BASE PAGE
    // ──────────────────────────────────────────────────
    await page.goto(`${BASE_URL}/knowledge-base`);
    await expect(
      page.getByText("Golden Corp Capability Statement")
    ).toBeVisible({ timeout: 10_000 });
  });
});
