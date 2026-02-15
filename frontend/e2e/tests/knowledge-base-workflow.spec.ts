import { test, expect } from "../fixtures/auth";

async function getAccessToken(page: Parameters<typeof test>[0]["authenticatedPage"]) {
  const token = await page.evaluate(() =>
    localStorage.getItem("rfp_sniper_access_token")
  );
  expect(token).toBeTruthy();
  return token as string;
}

test.describe("Knowledge Base Workflow", () => {
  test("uploads a document via API and verifies processing completes", async ({
    authenticatedPage: page,
  }) => {
    const token = await getAccessToken(page);
    const nonce = Date.now();

    // Create a small text file for upload
    const fileName = `e2e-kb-${nonce}.txt`;
    const fileContent = `Capability Statement - E2E Corp\n\nE2E Corp specializes in cloud modernization and AI/ML solutions for federal agencies. Our team has 10+ years of experience delivering secure IT services under FISMA and FedRAMP compliance frameworks.\n\nPast Performance:\n- Department of Defense Cloud Migration (2024-2025)\n- VA Digital Health Platform (2023-2024)\n\nNAICS: 541512, 541511\nClearance: Top Secret/SCI`;

    // Upload via multipart form API
    const formData = new FormData();
    formData.append("file", new Blob([fileContent], { type: "text/plain" }), fileName);
    formData.append("title", `E2E Capability Statement ${nonce}`);
    formData.append("document_type", "capability_statement");

    const uploadResponse = await page.request.post("/api/documents", {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        file: { name: fileName, mimeType: "text/plain", buffer: Buffer.from(fileContent) },
        title: `E2E Capability Statement ${nonce}`,
        document_type: "capability_statement",
      },
    });
    expect(uploadResponse.ok()).toBeTruthy();
    const uploaded = await uploadResponse.json();
    expect(uploaded.id).toBeTruthy();
    expect(["pending", "ready"]).toContain(uploaded.processing_status);

    // Poll for processing completion (Celery task)
    await expect
      .poll(
        async () => {
          const listResponse = await page.request.get(
            `/api/documents?ready_only=false`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          if (!listResponse.ok()) return "error";
          const { documents } = (await listResponse.json()) as {
            documents: Array<{ id: number; processing_status: string }>;
          };
          const doc = documents.find((d) => d.id === uploaded.id);
          return doc?.processing_status ?? "not_found";
        },
        { timeout: 30_000, intervals: [2_000] }
      )
      .toBe("ready");

    // Navigate to KB page and verify document appears
    await page.goto("/knowledge-base");
    await expect(
      page.getByText(`E2E Capability Statement ${nonce}`)
    ).toBeVisible({ timeout: 10_000 });

    // Verify stats updated
    await expect(page.getByText("Ready for AI")).toBeVisible();
  });

  test("lists and deletes a knowledge base document", async ({
    authenticatedPage: page,
  }) => {
    const token = await getAccessToken(page);
    const nonce = Date.now();

    // Upload a document
    const uploadResponse = await page.request.post("/api/documents", {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        file: {
          name: `e2e-delete-${nonce}.txt`,
          mimeType: "text/plain",
          buffer: Buffer.from("Document to be deleted."),
        },
        title: `E2E Delete Test ${nonce}`,
        document_type: "other",
      },
    });
    expect(uploadResponse.ok()).toBeTruthy();
    const uploaded = await uploadResponse.json();

    // Verify it appears in list
    const listResponse = await page.request.get("/api/documents", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(listResponse.ok()).toBeTruthy();
    const { documents } = await listResponse.json();
    expect(documents.some((d: { id: number }) => d.id === uploaded.id)).toBe(true);

    // Delete it (retry once — Celery worker may briefly lock the row)
    let deleteResponse = await page.request.delete(
      `/api/documents/${uploaded.id}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (!deleteResponse.ok()) {
      await page.waitForTimeout(2_000);
      deleteResponse = await page.request.delete(
        `/api/documents/${uploaded.id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
    }
    expect(deleteResponse.ok()).toBeTruthy();

    // Verify it's gone
    const listAfter = await page.request.get("/api/documents", {
      headers: { Authorization: `Bearer ${token}` },
    });
    const { documents: docsAfter } = await listAfter.json();
    expect(docsAfter.some((d: { id: number }) => d.id === uploaded.id)).toBe(false);
  });
});
