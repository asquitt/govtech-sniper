import api from "./client";
import type {
  Proposal,
  ProposalSection,
  ProposalFocusDocument,
  ProposalOutline,
  OutlineSection,
  SectionEvidence,
  SubmissionPackage,
  TaskResponse,
  TaskStatus,
  DraftRequest,
} from "@/types";

// =============================================================================
// Draft Generation Endpoints
// =============================================================================

export const draftApi = {
  listProposals: async (params?: { rfp_id?: number }): Promise<Proposal[]> => {
    const { data } = await api.get("/draft/proposals", { params });
    return data;
  },

  getProposal: async (proposalId: number): Promise<Proposal> => {
    const { data } = await api.get(`/draft/proposals/${proposalId}`);
    return data;
  },

  createProposal: async (
    rfpId: number,
    title: string
  ): Promise<Proposal> => {
    const { data } = await api.post("/draft/proposals", { rfp_id: rfpId, title });
    return data;
  },

  listSections: async (
    proposalId: number,
    params?: { status?: string }
  ): Promise<ProposalSection[]> => {
    const { data } = await api.get(`/draft/proposals/${proposalId}/sections`, {
      params,
    });
    return data;
  },

  getSection: async (sectionId: number): Promise<ProposalSection> => {
    const { data } = await api.get(`/draft/sections/${sectionId}`);
    return data;
  },

  updateSection: async (
    sectionId: number,
    payload: Partial<ProposalSection>
  ): Promise<ProposalSection> => {
    const { data } = await api.patch(`/draft/sections/${sectionId}`, payload);
    return data;
  },

  listSectionEvidence: async (sectionId: number): Promise<SectionEvidence[]> => {
    const { data } = await api.get(`/draft/sections/${sectionId}/evidence`);
    return data;
  },

  addSectionEvidence: async (
    sectionId: number,
    payload: { document_id: number; chunk_id?: number; citation?: string; notes?: string }
  ): Promise<SectionEvidence> => {
    const { data } = await api.post(`/draft/sections/${sectionId}/evidence`, payload);
    return data;
  },

  deleteSectionEvidence: async (
    sectionId: number,
    evidenceId: number
  ): Promise<{ message: string; evidence_id: number }> => {
    const { data } = await api.delete(
      `/draft/sections/${sectionId}/evidence/${evidenceId}`
    );
    return data;
  },

  listSubmissionPackages: async (
    proposalId: number
  ): Promise<SubmissionPackage[]> => {
    const { data } = await api.get(
      `/draft/proposals/${proposalId}/submission-packages`
    );
    return data;
  },

  createSubmissionPackage: async (
    proposalId: number,
    payload: {
      title: string;
      due_date?: string;
      owner_id?: number;
      checklist?: Record<string, unknown>[];
      notes?: string;
    }
  ): Promise<SubmissionPackage> => {
    const { data } = await api.post(
      `/draft/proposals/${proposalId}/submission-packages`,
      payload
    );
    return data;
  },

  updateSubmissionPackage: async (
    packageId: number,
    payload: Partial<SubmissionPackage>
  ): Promise<SubmissionPackage> => {
    const { data } = await api.patch(
      `/draft/submission-packages/${packageId}`,
      payload
    );
    return data;
  },

  submitSubmissionPackage: async (
    packageId: number
  ): Promise<SubmissionPackage> => {
    const { data } = await api.post(
      `/draft/submission-packages/${packageId}/submit`
    );
    return data;
  },

  generateFromMatrix: async (
    proposalId: number
  ): Promise<{ sections_created: number }> => {
    const { data } = await api.post(`/draft/proposals/${proposalId}/generate-from-matrix`);
    return data;
  },

  generateSection: async (
    requirementId: string,
    request?: DraftRequest
  ): Promise<TaskResponse> => {
    const { data } = await api.post(
      `/draft/${requirementId}`,
      request || { requirement_id: requirementId }
    );
    return data;
  },

  generateAllSections: async (
    proposalId: number,
    options?: { max_words?: number; tone?: string }
  ): Promise<TaskResponse> => {
    const { data } = await api.post(`/draft/proposals/${proposalId}/generate-all`, null, {
      params: options,
    });
    return data;
  },

  getGenerationStatus: async (taskId: string): Promise<TaskStatus> => {
    const { data } = await api.get(`/draft/${taskId}/status`);
    return data;
  },

  refreshCache: async (ttlHours?: number): Promise<TaskResponse> => {
    const { data } = await api.post("/draft/refresh-cache", null, {
      params: { ttl_hours: ttlHours },
    });
    return data;
  },

  listFocusDocuments: async (proposalId: number): Promise<ProposalFocusDocument[]> => {
    const { data } = await api.get(`/draft/proposals/${proposalId}/focus-documents`);
    return data;
  },

  setFocusDocuments: async (
    proposalId: number,
    documentIds: number[]
  ): Promise<ProposalFocusDocument[]> => {
    const { data } = await api.put(`/draft/proposals/${proposalId}/focus-documents`, {
      document_ids: documentIds,
    });
    return data;
  },

  removeFocusDocument: async (proposalId: number, documentId: number): Promise<void> => {
    await api.delete(`/draft/proposals/${proposalId}/focus-documents/${documentId}`);
  },

  generateOutline: async (proposalId: number): Promise<TaskResponse> => {
    const { data } = await api.post(`/draft/proposals/${proposalId}/generate-outline`);
    return data;
  },

  getOutline: async (proposalId: number): Promise<ProposalOutline> => {
    const { data } = await api.get(`/draft/proposals/${proposalId}/outline`);
    return data;
  },

  addOutlineSection: async (
    proposalId: number,
    payload: { title: string; parent_id?: number; description?: string; display_order?: number }
  ): Promise<OutlineSection> => {
    const { data } = await api.post(`/draft/proposals/${proposalId}/outline/sections`, payload);
    return data;
  },

  updateOutlineSection: async (
    proposalId: number,
    sectionId: number,
    payload: Partial<OutlineSection>
  ): Promise<OutlineSection> => {
    const { data } = await api.patch(
      `/draft/proposals/${proposalId}/outline/sections/${sectionId}`,
      payload
    );
    return data;
  },

  deleteOutlineSection: async (proposalId: number, sectionId: number): Promise<void> => {
    await api.delete(`/draft/proposals/${proposalId}/outline/sections/${sectionId}`);
  },

  approveOutline: async (proposalId: number): Promise<{ sections_created: number }> => {
    const { data } = await api.post(`/draft/proposals/${proposalId}/outline/approve`);
    return data;
  },

  rewriteSection: async (
    sectionId: number,
    payload: { tone: string; instructions?: string }
  ): Promise<ProposalSection> => {
    const { data } = await api.post(`/draft/sections/${sectionId}/rewrite`, payload);
    return data;
  },

  expandSection: async (
    sectionId: number,
    payload: { target_words: number; focus_area?: string }
  ): Promise<ProposalSection> => {
    const { data } = await api.post(`/draft/sections/${sectionId}/expand`, payload);
    return data;
  },

  getGenerationProgress: async (
    proposalId: number
  ): Promise<{
    total: number;
    completed: number;
    pending: number;
    generating: number;
    completion_percentage: number;
  }> => {
    const { data } = await api.get(
      `/draft/proposals/${proposalId}/generation-progress`
    );
    return data;
  },
};
