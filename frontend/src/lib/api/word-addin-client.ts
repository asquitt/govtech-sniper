import api from "./client";

// =============================================================================
// Word Add-in Section Sync + AI Endpoints
// =============================================================================

export interface SectionPullData {
  section_id: number;
  title: string;
  content: string;
  requirements: string[];
  last_modified: string | null;
}

export interface ComplianceCheckResult {
  section_id: number;
  compliant: boolean;
  score?: number;
  issues: Array<{
    paragraph_snippet?: string;
    issue: string;
    severity?: string;
    suggestion?: string;
  }>;
  suggestions: string[];
}

export interface RewriteResult {
  original_length: number;
  rewritten: string;
  rewritten_length: number;
  mode: string;
}

export const wordAddinSyncApi = {
  pullSection: async (sectionId: number): Promise<SectionPullData> => {
    const { data } = await api.post(`/word-addin/sections/${sectionId}/pull`);
    return data;
  },

  pushSection: async (
    sectionId: number,
    content: string
  ): Promise<{ message: string; section_id: number }> => {
    const { data } = await api.post(`/word-addin/sections/${sectionId}/push`, {
      content,
    });
    return data;
  },

  checkCompliance: async (
    sectionId: number
  ): Promise<ComplianceCheckResult> => {
    const { data } = await api.post(
      `/word-addin/sections/${sectionId}/compliance-check`
    );
    return data;
  },

  rewriteContent: async (
    content: string,
    mode: "shorten" | "expand" | "improve"
  ): Promise<RewriteResult> => {
    const { data } = await api.post("/word-addin/ai/rewrite", {
      content,
      mode,
    });
    return data;
  },
};
