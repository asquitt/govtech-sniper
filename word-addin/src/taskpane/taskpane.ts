/**
 * RFP Sniper Word Add-in - Task Pane
 * Handles section sync, AI rewrite, and compliance checking.
 */

const API_BASE = "http://localhost:8000/api/v1/word-addin";

interface SectionData {
  section_id: number;
  title: string;
  content: string;
  requirements: string[];
  last_modified: string | null;
}

interface ComplianceResult {
  section_id: number;
  compliant: boolean;
  issues: string[];
  suggestions: string[];
}

interface RewriteResult {
  original_length: number;
  rewritten: string;
  rewritten_length: number;
  mode: string;
}

let authToken = "";

function setStatus(message: string): void {
  const el = document.getElementById("status");
  if (el) el.textContent = message;
}

async function apiCall<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
      ...options.headers,
    },
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

async function pullSection(sectionId: number): Promise<void> {
  setStatus("Pulling section...");
  try {
    const data = await apiCall<SectionData>(`/sections/${sectionId}/pull`, {
      method: "POST",
    });
    // In a real Office.js add-in, we'd insert into the document:
    // await Word.run(async (context) => { ... });
    setStatus(`Pulled: ${data.title} (${data.content.length} chars)`);
    console.log("Section content:", data);
  } catch (err) {
    setStatus(`Error: ${err instanceof Error ? err.message : "Unknown error"}`);
  }
}

async function pushSection(
  sectionId: number,
  content: string,
): Promise<void> {
  setStatus("Pushing section...");
  try {
    await apiCall(`/sections/${sectionId}/push`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
    setStatus("Section pushed successfully");
  } catch (err) {
    setStatus(`Error: ${err instanceof Error ? err.message : "Unknown error"}`);
  }
}

async function checkCompliance(sectionId: number): Promise<void> {
  setStatus("Checking compliance...");
  try {
    const result = await apiCall<ComplianceResult>(
      `/sections/${sectionId}/compliance-check`,
      { method: "POST" },
    );
    if (result.compliant) {
      setStatus("Section is compliant");
    } else {
      setStatus(`${result.issues.length} issues found`);
    }
    console.log("Compliance result:", result);
  } catch (err) {
    setStatus(`Error: ${err instanceof Error ? err.message : "Unknown error"}`);
  }
}

async function rewriteContent(
  content: string,
  mode: string,
): Promise<string> {
  setStatus(`Rewriting (${mode})...`);
  try {
    const result = await apiCall<RewriteResult>("/ai/rewrite", {
      method: "POST",
      body: JSON.stringify({ content, mode }),
    });
    setStatus(
      `Rewritten: ${result.original_length} -> ${result.rewritten_length} chars`,
    );
    return result.rewritten;
  } catch (err) {
    setStatus(`Error: ${err instanceof Error ? err.message : "Unknown error"}`);
    return content;
  }
}

// Export for use in HTML
(globalThis as Record<string, unknown>).rfpSniper = {
  pullSection,
  pushSection,
  checkCompliance,
  rewriteContent,
  setAuthToken: (token: string) => {
    authToken = token;
  },
};
