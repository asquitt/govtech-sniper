import axios from "axios";
import type {
  RFP,
  RFPListItem,
  ComplianceMatrix,
  ComplianceRequirement,
  Proposal,
  ProposalSection,
  ProposalFocusDocument,
  ProposalOutline,
  OutlineSection,
  SectionEvidence,
  SubmissionPackage,
  KnowledgeBaseDocument,
  CapturePlan,
  CapturePlanListItem,
  CaptureStage,
  BidDecision,
  GateReview,
  TeamingPartner,
  TeamingPartnerLink,
  CaptureCustomField,
  CaptureFieldValueList,
  CaptureFieldValue,
  CaptureFieldType,
  CaptureCompetitor,
  CaptureMatchInsight,
  ContractAward,
  ContractDeliverable,
  ContractStatus,
  DeliverableStatus,
  ContractTask,
  CPARSReview,
  CPARSEvidence,
  ContractStatusReport,
  DashSession,
  DashMessage,
  IntegrationConfig,
  IntegrationProvider,
  IntegrationProviderDefinition,
  IntegrationTestResult,
  IntegrationSyncRun,
  IntegrationWebhookEvent,
  IntegrationSsoAuthorizeResponse,
  SavedSearch,
  SavedSearchRunResult,
  AwardRecord,
  OpportunityContact,
  BudgetIntelligence,
  WordAddinSession,
  WordAddinSessionStatus,
  WordAddinEvent,
  ProposalGraphicRequest,
  GraphicsRequestStatus,
  AuditEvent,
  AuditSummary,
  ObservabilityMetrics,
  TaskResponse,
  TaskStatus,
  SAMSearchParams,
  DraftRequest,
} from "@/types";

// =============================================================================
// API Client Configuration
// =============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
});

// Token storage keys
const ACCESS_TOKEN_KEY = "rfp_sniper_access_token";
const REFRESH_TOKEN_KEY = "rfp_sniper_refresh_token";

// =============================================================================
// Auth Token Management
// =============================================================================

export const tokenManager = {
  getAccessToken: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },

  getRefreshToken: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  setTokens: (accessToken: string, refreshToken: string): void => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },

  clearTokens: (): void => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },

  isAuthenticated: (): boolean => {
    return !!tokenManager.getAccessToken();
  },
};

// Add auth header interceptor
api.interceptors.request.use(
  (config) => {
    const token = tokenManager.getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and not already retrying, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = tokenManager.getRefreshToken();
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });

          tokenManager.setTokens(data.access_token, data.refresh_token);

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed, clear tokens and redirect to login
          tokenManager.clearTokens();
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
        }
      }
    }

    return Promise.reject(error);
  }
);

// =============================================================================
// Auth Endpoints
// =============================================================================

export const authApi = {
  register: async (data: {
    email: string;
    password: string;
    full_name: string;
    company_name?: string;
  }): Promise<{ access_token: string; refresh_token: string }> => {
    const response = await api.post("/auth/register", data);
    tokenManager.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  },

  login: async (email: string, password: string): Promise<{ access_token: string; refresh_token: string }> => {
    const response = await api.post("/auth/login", { email, password });
    tokenManager.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  },

  logout: async (): Promise<void> => {
    try {
      await api.post("/auth/logout");
    } finally {
      tokenManager.clearTokens();
    }
  },

  getMe: async (): Promise<{
    id: number;
    email: string;
    full_name: string | null;
    company_name: string | null;
    tier: string;
    api_calls_today: number;
    api_calls_limit: number;
  }> => {
    const { data } = await api.get("/auth/me");
    return data;
  },

  getProfile: async (): Promise<{
    naics_codes: string[];
    clearance_level: string;
    set_aside_types: string[];
    preferred_states: string[];
    min_contract_value: number | null;
    max_contract_value: number | null;
    include_keywords: string[];
    exclude_keywords: string[];
  }> => {
    const { data } = await api.get("/auth/profile");
    return data;
  },

  updateProfile: async (profile: {
    naics_codes?: string[];
    clearance_level?: string;
    set_aside_types?: string[];
    preferred_states?: string[];
    min_contract_value?: number;
    max_contract_value?: number;
    include_keywords?: string[];
    exclude_keywords?: string[];
  }): Promise<{ message: string }> => {
    const { data } = await api.put("/auth/profile", profile);
    return data;
  },

  changePassword: async (currentPassword: string, newPassword: string): Promise<{ message: string }> => {
    const { data } = await api.post("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return data;
  },
};

// =============================================================================
// RFP Endpoints
// =============================================================================

export const rfpApi = {
  list: async (params?: {
    status?: string;
    qualified_only?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<RFPListItem[]> => {
    const { data } = await api.get("/rfps", { params });
    return data;
  },

  get: async (rfpId: number): Promise<RFP> => {
    const { data } = await api.get(`/rfps/${rfpId}`);
    return data;
  },

  getSnapshots: async (
    rfpId: number,
    params?: { include_raw?: boolean; limit?: number }
  ): Promise<
    {
      id: number;
      notice_id: string;
      solicitation_number?: string | null;
      rfp_id: number;
      user_id?: number | null;
      fetched_at: string;
      posted_date?: string | null;
      response_deadline?: string | null;
      raw_hash: string;
      summary: Record<string, unknown>;
      raw_payload?: Record<string, unknown> | null;
    }[]
  > => {
    const { data } = await api.get(`/rfps/${rfpId}/snapshots`, { params });
    return data;
  },

  getSnapshotDiff: async (
    rfpId: number,
    params?: { from_snapshot_id?: number; to_snapshot_id?: number }
  ): Promise<{
    from_snapshot_id: number;
    to_snapshot_id: number;
    changes: { field: string; before?: string | null; after?: string | null }[];
    summary_from: Record<string, unknown>;
    summary_to: Record<string, unknown>;
  }> => {
    const { data } = await api.get(`/rfps/${rfpId}/snapshots/diff`, { params });
    return {
      ...data,
      changes: (data.changes || []).map((change: {
        field: string;
        from_value?: string | null;
        to_value?: string | null;
        before?: string | null;
        after?: string | null;
      }) => ({
        field: change.field,
        before: change.before ?? change.from_value ?? null,
        after: change.after ?? change.to_value ?? null,
      })),
    };
  },

  create: async (rfp: Partial<RFP>): Promise<RFP> => {
    const { data } = await api.post("/rfps", rfp);
    return data;
  },

  update: async (rfpId: number, updates: Partial<RFP>): Promise<RFP> => {
    const { data } = await api.patch(`/rfps/${rfpId}`, updates);
    return data;
  },

  delete: async (rfpId: number): Promise<void> => {
    await api.delete(`/rfps/${rfpId}`);
  },

  getStats: async (): Promise<{
    total: number;
    by_status: Record<string, number>;
    qualified: number;
    disqualified: number;
    pending_filter: number;
  }> => {
    const { data } = await api.get("/rfps/stats/summary");
    return data;
  },
};

// =============================================================================
// Saved Search Endpoints
// =============================================================================

export const savedSearchApi = {
  list: async (): Promise<SavedSearch[]> => {
    const { data } = await api.get("/saved-searches");
    return data;
  },

  create: async (payload: {
    name: string;
    filters: Record<string, unknown>;
    is_active?: boolean;
  }): Promise<SavedSearch> => {
    const { data } = await api.post("/saved-searches", payload);
    return data;
  },

  update: async (
    searchId: number,
    payload: Partial<{ name: string; filters: Record<string, unknown>; is_active: boolean }>
  ): Promise<SavedSearch> => {
    const { data } = await api.patch(`/saved-searches/${searchId}`, payload);
    return data;
  },

  remove: async (searchId: number): Promise<void> => {
    await api.delete(`/saved-searches/${searchId}`);
  },

  run: async (searchId: number): Promise<SavedSearchRunResult> => {
    const { data } = await api.post(`/saved-searches/${searchId}/run`, {});
    return data;
  },
};

// =============================================================================
// Award Intelligence Endpoints
// =============================================================================

export const awardApi = {
  list: async (params?: { rfp_id?: number }): Promise<AwardRecord[]> => {
    const { data } = await api.get("/awards", { params });
    return data;
  },

  create: async (payload: Partial<AwardRecord>): Promise<AwardRecord> => {
    const { data } = await api.post("/awards", payload);
    return data;
  },

  update: async (
    awardId: number,
    payload: Partial<AwardRecord>
  ): Promise<AwardRecord> => {
    const { data } = await api.patch(`/awards/${awardId}`, payload);
    return data;
  },

  remove: async (awardId: number): Promise<void> => {
    await api.delete(`/awards/${awardId}`);
  },
};

// =============================================================================
// Opportunity Contact Endpoints
// =============================================================================

export const contactApi = {
  list: async (params?: { rfp_id?: number }): Promise<OpportunityContact[]> => {
    const { data } = await api.get("/contacts", { params });
    return data;
  },

  create: async (payload: Partial<OpportunityContact>): Promise<OpportunityContact> => {
    const { data } = await api.post("/contacts", payload);
    return data;
  },

  update: async (
    contactId: number,
    payload: Partial<OpportunityContact>
  ): Promise<OpportunityContact> => {
    const { data } = await api.patch(`/contacts/${contactId}`, payload);
    return data;
  },

  remove: async (contactId: number): Promise<void> => {
    await api.delete(`/contacts/${contactId}`);
  },
};

// =============================================================================
// Word Add-in Endpoints
// =============================================================================

export const wordAddinApi = {
  listSessions: async (params?: { proposal_id?: number }): Promise<WordAddinSession[]> => {
    const { data } = await api.get("/word-addin/sessions", { params });
    return data;
  },

  createSession: async (payload: {
    proposal_id: number;
    document_name: string;
    metadata?: Record<string, unknown>;
  }): Promise<WordAddinSession> => {
    const { data } = await api.post("/word-addin/sessions", payload);
    return data;
  },

  updateSession: async (
    sessionId: number,
    payload: Partial<{
      document_name: string;
      status: WordAddinSessionStatus;
      metadata: Record<string, unknown>;
    }>
  ): Promise<WordAddinSession> => {
    const { data } = await api.patch(`/word-addin/sessions/${sessionId}`, payload);
    return data;
  },

  createEvent: async (
    sessionId: number,
    payload: { event_type: string; payload?: Record<string, unknown> }
  ): Promise<WordAddinEvent> => {
    const { data } = await api.post(`/word-addin/sessions/${sessionId}/events`, payload);
    return data;
  },

  listEvents: async (sessionId: number): Promise<WordAddinEvent[]> => {
    const { data } = await api.get(`/word-addin/sessions/${sessionId}/events`);
    return data;
  },
};

// =============================================================================
// Graphics Requests Endpoints
// =============================================================================

export const graphicsApi = {
  listRequests: async (params?: { proposal_id?: number }): Promise<ProposalGraphicRequest[]> => {
    const { data } = await api.get("/graphics", { params });
    return data;
  },

  createRequest: async (payload: {
    proposal_id: number;
    title: string;
    description?: string;
    section_id?: number;
    due_date?: string;
  }): Promise<ProposalGraphicRequest> => {
    const { data } = await api.post("/graphics", payload);
    return data;
  },

  updateRequest: async (
    requestId: number,
    payload: Partial<{
      title: string;
      description: string;
      section_id: number | null;
      due_date: string | null;
      status: GraphicsRequestStatus;
      asset_url: string | null;
      notes: string | null;
    }>
  ): Promise<ProposalGraphicRequest> => {
    const { data } = await api.patch(`/graphics/${requestId}`, payload);
    return data;
  },

  removeRequest: async (requestId: number): Promise<void> => {
    await api.delete(`/graphics/${requestId}`);
  },
};

// =============================================================================
// Ingest Endpoints
// =============================================================================

export const ingestApi = {
  triggerSamSearch: async (
    params: SAMSearchParams
  ): Promise<TaskResponse> => {
    const { data } = await api.post("/ingest/sam", params);
    return data;
  },

  getTaskStatus: async (taskId: string): Promise<TaskStatus> => {
    const { data } = await api.get(`/ingest/sam/status/${taskId}`);
    return data;
  },

  quickSearch: async (
    keywords: string,
    limit?: number
  ): Promise<{ count: number; opportunities: unknown[] }> => {
    const { data } = await api.post("/ingest/sam/quick-search", null, {
      params: { keywords, limit },
    });
    return data;
  },
};

// =============================================================================
// Analysis Endpoints
// =============================================================================

export const analysisApi = {
  triggerAnalysis: async (
    rfpId: number,
    forceReanalyze?: boolean
  ): Promise<TaskResponse> => {
    const { data } = await api.post(`/analyze/${rfpId}`, null, {
      params: { force_reanalyze: forceReanalyze },
    });
    return data;
  },

  getTaskStatus: async (
    rfpId: number,
    taskId: string
  ): Promise<TaskStatus> => {
    const { data } = await api.get(`/analyze/${rfpId}/status/${taskId}`);
    return data;
  },

  getComplianceMatrix: async (rfpId: number): Promise<ComplianceMatrix> => {
    const { data } = await api.get(`/analyze/${rfpId}/matrix`);
    return data;
  },

  addRequirement: async (
    rfpId: number,
    payload: Partial<ComplianceRequirement>
  ): Promise<ComplianceMatrix> => {
    const { data } = await api.post(`/analyze/${rfpId}/matrix`, payload);
    return data;
  },

  updateRequirement: async (
    rfpId: number,
    requirementId: string,
    payload: Partial<ComplianceRequirement>
  ): Promise<ComplianceMatrix> => {
    const { data } = await api.patch(
      `/analyze/${rfpId}/matrix/${requirementId}`,
      payload
    );
    return data;
  },

  deleteRequirement: async (
    rfpId: number,
    requirementId: string
  ): Promise<{ message: string; requirement_id: string }> => {
    const { data } = await api.delete(
      `/analyze/${rfpId}/matrix/${requirementId}`
    );
    return data;
  },

  triggerKillerFilter: async (rfpId: number): Promise<TaskResponse> => {
    const { data } = await api.post(`/analyze/${rfpId}/filter`);
    return data;
  },
};

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
};

// =============================================================================
// Document Endpoints
// =============================================================================

export const documentApi = {
  list: async (params?: {
    document_type?: string;
    ready_only?: boolean;
  }): Promise<KnowledgeBaseDocument[]> => {
    const { data } = await api.get("/documents", { params });
    return data.documents ?? [];
  },

  get: async (documentId: number): Promise<KnowledgeBaseDocument> => {
    const { data } = await api.get(`/documents/${documentId}`);
    return data;
  },

  upload: async (
    file: File,
    metadata: {
      title: string;
      document_type: string;
      description?: string;
    }
  ): Promise<KnowledgeBaseDocument> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", metadata.title);
    formData.append("document_type", metadata.document_type);
    if (metadata.description) {
      formData.append("description", metadata.description);
    }

    const { data } = await api.post("/documents", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  update: async (
    documentId: number,
    updates: Partial<KnowledgeBaseDocument>
  ): Promise<KnowledgeBaseDocument> => {
    const { data } = await api.patch(`/documents/${documentId}`, updates);
    return data;
  },

  delete: async (documentId: number): Promise<void> => {
    await api.delete(`/documents/${documentId}`);
  },

  getTypes: async (): Promise<{ value: string; label: string }[]> => {
    const { data } = await api.get("/documents/types/list");
    return data;
  },
};

// =============================================================================
// Export Endpoints
// =============================================================================

export const exportApi = {
  exportProposalDocx: async (proposalId: number): Promise<Blob> => {
    const { data } = await api.get(`/export/proposals/${proposalId}/docx`, {
      responseType: "blob",
    });
    return data;
  },

  exportProposalPdf: async (proposalId: number): Promise<Blob> => {
    const { data } = await api.get(`/export/proposals/${proposalId}/pdf`, {
      responseType: "blob",
    });
    return data;
  },

  exportComplianceMatrix: async (
    rfpId: number,
    format: "xlsx" | "csv" = "xlsx"
  ): Promise<Blob> => {
    const safeFormat = format === "csv" ? "xlsx" : format;
    const { data } = await api.get(
      `/export/rfps/${rfpId}/compliance-matrix/${safeFormat}`,
      {
      responseType: "blob",
      }
    );
    return data;
  },
};

// =============================================================================
// Capture Endpoints
// =============================================================================

export const captureApi = {
  listPlans: async (): Promise<CapturePlanListItem[]> => {
    const { data } = await api.get("/capture/plans", { params: { include_rfp: true } });
    return data.plans ?? data;
  },

  listFields: async (): Promise<CaptureCustomField[]> => {
    const { data } = await api.get("/capture/fields");
    return data;
  },

  createField: async (payload: {
    name: string;
    field_type?: CaptureFieldType;
    options?: string[];
    stage?: CaptureStage | null;
    is_required?: boolean;
  }): Promise<CaptureCustomField> => {
    const { data } = await api.post("/capture/fields", payload);
    return data;
  },

  updateField: async (
    fieldId: number,
    payload: Partial<{
      name: string;
      field_type: CaptureFieldType;
      options: string[];
      stage: CaptureStage | null;
      is_required: boolean;
    }>
  ): Promise<CaptureCustomField> => {
    const { data } = await api.patch(`/capture/fields/${fieldId}`, payload);
    return data;
  },

  removeField: async (fieldId: number): Promise<void> => {
    await api.delete(`/capture/fields/${fieldId}`);
  },

  listPlanFields: async (planId: number): Promise<CaptureFieldValueList> => {
    const { data } = await api.get(`/capture/plans/${planId}/fields`);
    return data;
  },

  getMatchInsight: async (planId: number): Promise<CaptureMatchInsight> => {
    const { data } = await api.get(`/capture/plans/${planId}/match-insight`);
    return data;
  },

  savePlanFields: async (
    planId: number,
    payload: CaptureFieldValue[]
  ): Promise<CaptureFieldValueList> => {
    const { data } = await api.put(
      `/capture/plans/${planId}/fields`,
      payload.map((item) => ({ field_id: item.field.id, value: item.value }))
    );
    return data;
  },

  createPlan: async (payload: {
    rfp_id: number;
    stage?: CaptureStage;
    bid_decision?: BidDecision;
    win_probability?: number | null;
    notes?: string | null;
  }): Promise<CapturePlan> => {
    const { data } = await api.post("/capture/plans", payload);
    return data;
  },

  updatePlan: async (
    planId: number,
    payload: Partial<{
      stage: CaptureStage;
      bid_decision: BidDecision;
      win_probability: number | null;
      notes: string | null;
    }>
  ): Promise<CapturePlan> => {
    const { data } = await api.patch(`/capture/plans/${planId}`, payload);
    return data;
  },

  listGateReviews: async (rfpId: number): Promise<GateReview[]> => {
    const { data } = await api.get("/capture/gate-reviews", {
      params: { rfp_id: rfpId },
    });
    return data;
  },

  createGateReview: async (payload: {
    rfp_id: number;
    stage?: CaptureStage;
    decision?: BidDecision;
    notes?: string | null;
  }): Promise<GateReview> => {
    const { data } = await api.post("/capture/gate-reviews", payload);
    return data;
  },

  listPartners: async (): Promise<TeamingPartner[]> => {
    const { data } = await api.get("/capture/partners");
    return data;
  },

  createPartner: async (payload: {
    name: string;
    partner_type?: string | null;
    contact_name?: string | null;
    contact_email?: string | null;
    notes?: string | null;
  }): Promise<TeamingPartner> => {
    const { data } = await api.post("/capture/partners", payload);
    return data;
  },

  linkPartner: async (payload: {
    rfp_id: number;
    partner_id: number;
    role?: string | null;
  }): Promise<TeamingPartnerLink> => {
    const { data } = await api.post("/capture/partners/link", payload);
    return data;
  },

  listPartnerLinks: async (rfpId: number): Promise<{
    links: TeamingPartnerLink[];
    total: number;
  }> => {
    const { data } = await api.get("/capture/partners/links", {
      params: { rfp_id: rfpId },
    });
    return data;
  },

  listCompetitors: async (rfpId: number): Promise<CaptureCompetitor[]> => {
    const { data } = await api.get("/capture/competitors", {
      params: { rfp_id: rfpId },
    });
    return data;
  },

  createCompetitor: async (payload: {
    rfp_id: number;
    name: string;
    incumbent?: boolean;
    strengths?: string | null;
    weaknesses?: string | null;
    notes?: string | null;
  }): Promise<CaptureCompetitor> => {
    const { data } = await api.post("/capture/competitors", payload);
    return data;
  },

  updateCompetitor: async (
    competitorId: number,
    payload: Partial<{
      name: string;
      incumbent: boolean;
      strengths: string | null;
      weaknesses: string | null;
      notes: string | null;
    }>
  ): Promise<CaptureCompetitor> => {
    const { data } = await api.patch(`/capture/competitors/${competitorId}`, payload);
    return data;
  },

  removeCompetitor: async (competitorId: number): Promise<void> => {
    await api.delete(`/capture/competitors/${competitorId}`);
  },
};

// =============================================================================
// Budget Intelligence Endpoints
// =============================================================================

export const budgetIntelApi = {
  list: async (params?: { rfp_id?: number }): Promise<BudgetIntelligence[]> => {
    const { data } = await api.get("/budget-intel", { params });
    return data;
  },

  create: async (payload: {
    rfp_id?: number;
    title: string;
    fiscal_year?: number;
    amount?: number;
    source_url?: string;
    notes?: string;
  }): Promise<BudgetIntelligence> => {
    const { data } = await api.post("/budget-intel", payload);
    return data;
  },

  update: async (
    recordId: number,
    payload: Partial<{
      title: string;
      fiscal_year: number;
      amount: number;
      source_url: string;
      notes: string;
    }>
  ): Promise<BudgetIntelligence> => {
    const { data } = await api.patch(`/budget-intel/${recordId}`, payload);
    return data;
  },

  remove: async (recordId: number): Promise<void> => {
    await api.delete(`/budget-intel/${recordId}`);
  },
};

// =============================================================================
// Contract Endpoints
// =============================================================================

export const contractApi = {
  list: async (): Promise<{ contracts: ContractAward[]; total: number }> => {
    const { data } = await api.get("/contracts");
    return data;
  },

  create: async (payload: {
    contract_number: string;
    title: string;
    agency?: string | null;
    status?: ContractStatus;
    value?: number | null;
  }): Promise<ContractAward> => {
    const { data } = await api.post("/contracts", payload);
    return data;
  },

  update: async (
    contractId: number,
    payload: Partial<{
      title: string;
      agency: string | null;
      status: ContractStatus;
      value: number | null;
    }>
  ): Promise<ContractAward> => {
    const { data } = await api.patch(`/contracts/${contractId}`, payload);
    return data;
  },

  listDeliverables: async (contractId: number): Promise<ContractDeliverable[]> => {
    const { data } = await api.get(`/contracts/${contractId}/deliverables`);
    return data;
  },

  createDeliverable: async (
    contractId: number,
    payload: { title: string; status?: DeliverableStatus }
  ): Promise<ContractDeliverable> => {
    const { data } = await api.post(`/contracts/${contractId}/deliverables`, payload);
    return data;
  },

  listTasks: async (contractId: number): Promise<ContractTask[]> => {
    const { data } = await api.get(`/contracts/${contractId}/tasks`);
    return data;
  },

  createTask: async (
    contractId: number,
    payload: { title: string }
  ): Promise<ContractTask> => {
    const { data } = await api.post(`/contracts/${contractId}/tasks`, payload);
    return data;
  },

  listCPARS: async (contractId: number): Promise<CPARSReview[]> => {
    const { data } = await api.get(`/contracts/${contractId}/cpars`);
    return data;
  },

  createCPARS: async (
    contractId: number,
    payload: { overall_rating?: string; notes?: string }
  ): Promise<CPARSReview> => {
    const { data } = await api.post(`/contracts/${contractId}/cpars`, payload);
    return data;
  },

  listCPARSEvidence: async (
    contractId: number,
    cparsId: number
  ): Promise<CPARSEvidence[]> => {
    const { data } = await api.get(
      `/contracts/${contractId}/cpars/${cparsId}/evidence`
    );
    return data;
  },

  addCPARSEvidence: async (
    contractId: number,
    cparsId: number,
    payload: { document_id: number; citation?: string; notes?: string }
  ): Promise<CPARSEvidence> => {
    const { data } = await api.post(
      `/contracts/${contractId}/cpars/${cparsId}/evidence`,
      payload
    );
    return data;
  },

  deleteCPARSEvidence: async (
    contractId: number,
    cparsId: number,
    evidenceId: number
  ): Promise<void> => {
    await api.delete(
      `/contracts/${contractId}/cpars/${cparsId}/evidence/${evidenceId}`
    );
  },

  listStatusReports: async (
    contractId: number
  ): Promise<ContractStatusReport[]> => {
    const { data } = await api.get(`/contracts/${contractId}/status-reports`);
    return data;
  },

  createStatusReport: async (
    contractId: number,
    payload: {
      period_start?: string;
      period_end?: string;
      summary?: string;
      accomplishments?: string;
      risks?: string;
      next_steps?: string;
    }
  ): Promise<ContractStatusReport> => {
    const { data } = await api.post(
      `/contracts/${contractId}/status-reports`,
      payload
    );
    return data;
  },

  updateStatusReport: async (
    reportId: number,
    payload: Partial<ContractStatusReport>
  ): Promise<ContractStatusReport> => {
    const { data } = await api.patch(
      `/contracts/status-reports/${reportId}`,
      payload
    );
    return data;
  },

  deleteStatusReport: async (reportId: number): Promise<void> => {
    await api.delete(`/contracts/status-reports/${reportId}`);
  },
};

// =============================================================================
// Dash Endpoints
// =============================================================================

export const dashApi = {
  listSessions: async (): Promise<DashSession[]> => {
    const { data } = await api.get("/dash/sessions");
    return data;
  },

  createSession: async (title?: string): Promise<DashSession> => {
    const { data } = await api.post("/dash/sessions", { title });
    return data;
  },

  addMessage: async (
    sessionId: number,
    payload: { role: "user" | "assistant"; content: string }
  ): Promise<DashMessage> => {
    const { data } = await api.post(`/dash/sessions/${sessionId}/messages`, payload);
    return data;
  },

  ask: async (payload: {
    question: string;
    rfp_id?: number;
  }): Promise<{ answer: string; citations: Record<string, unknown>[] }> => {
    const { data } = await api.post("/dash/ask", payload);
    return data;
  },
};

// =============================================================================
// Integration Endpoints
// =============================================================================

export const integrationApi = {
  providers: async (): Promise<IntegrationProviderDefinition[]> => {
    const { data } = await api.get("/integrations/providers");
    return data;
  },

  list: async (params?: { provider?: IntegrationProvider }): Promise<IntegrationConfig[]> => {
    const { data } = await api.get("/integrations", { params });
    return data;
  },

  create: async (payload: {
    provider: IntegrationProvider;
    name?: string | null;
    is_enabled?: boolean;
    config?: Record<string, unknown>;
  }): Promise<IntegrationConfig> => {
    const { data } = await api.post("/integrations", payload);
    return data;
  },

  update: async (
    integrationId: number,
    payload: Partial<{
      name: string | null;
      is_enabled: boolean;
      config: Record<string, unknown>;
    }>
  ): Promise<IntegrationConfig> => {
    const { data } = await api.patch(`/integrations/${integrationId}`, payload);
    return data;
  },

  remove: async (integrationId: number): Promise<void> => {
    await api.delete(`/integrations/${integrationId}`);
  },

  test: async (integrationId: number): Promise<IntegrationTestResult> => {
    const { data } = await api.post(`/integrations/${integrationId}/test`, {});
    return data;
  },

  authorizeSso: async (integrationId: number): Promise<IntegrationSsoAuthorizeResponse> => {
    const { data } = await api.post(`/integrations/${integrationId}/sso/authorize`, {});
    return data;
  },

  ssoCallback: async (integrationId: number, code: string): Promise<{ status: string }> => {
    const { data } = await api.post(`/integrations/${integrationId}/sso/callback`, { code });
    return data;
  },

  sync: async (integrationId: number): Promise<IntegrationSyncRun> => {
    const { data } = await api.post(`/integrations/${integrationId}/sync`, {});
    return data;
  },

  syncs: async (integrationId: number): Promise<IntegrationSyncRun[]> => {
    const { data } = await api.get(`/integrations/${integrationId}/syncs`);
    return data;
  },

  sendWebhook: async (
    integrationId: number,
    payload: Record<string, unknown>
  ): Promise<IntegrationWebhookEvent> => {
    const { data } = await api.post(`/integrations/${integrationId}/webhook`, payload);
    return data;
  },

  listWebhooks: async (integrationId: number): Promise<IntegrationWebhookEvent[]> => {
    const { data } = await api.get(`/integrations/${integrationId}/webhooks`);
    return data;
  },
};

// =============================================================================
// Template Endpoints
// =============================================================================

export interface ProposalTemplate {
  id: number;
  name: string;
  description: string;
  category: string;
  content_template: string;
  placeholders: string[];
  is_system: boolean;
  created_at: string;
}

export const templateApi = {
  list: async (params?: {
    category?: string;
    include_system?: boolean;
  }): Promise<ProposalTemplate[]> => {
    const { data } = await api.get("/templates", { params });
    return data;
  },

  get: async (templateId: number): Promise<ProposalTemplate> => {
    const { data } = await api.get(`/templates/${templateId}`);
    return data;
  },

  create: async (template: {
    name: string;
    description?: string;
    category: string;
    content_template: string;
  }): Promise<ProposalTemplate> => {
    const { data } = await api.post("/templates", template);
    return data;
  },

  update: async (
    templateId: number,
    updates: Partial<ProposalTemplate>
  ): Promise<ProposalTemplate> => {
    const { data } = await api.patch(`/templates/${templateId}`, updates);
    return data;
  },

  delete: async (templateId: number): Promise<void> => {
    await api.delete(`/templates/${templateId}`);
  },

  apply: async (
    templateId: number,
    variables: Record<string, string>
  ): Promise<{ content: string }> => {
    const { data } = await api.post(`/templates/${templateId}/apply`, {
      variables,
    });
    return data;
  },

  getCategories: async (): Promise<{ value: string; label: string }[]> => {
    const { data } = await api.get("/templates/categories/list");
    return data;
  },
};

// =============================================================================
// Analytics Endpoints
// =============================================================================

export interface DashboardMetrics {
  rfp_stats: {
    total: number;
    qualified: number;
    disqualified: number;
    pending: number;
    by_status: Record<string, number>;
  };
  proposal_stats: {
    total: number;
    in_progress: number;
    completed: number;
    submitted: number;
    avg_completion_rate: number;
  };
  document_stats: {
    total: number;
    by_type: Record<string, number>;
    total_size_mb: number;
  };
  ai_usage: {
    analyses_today: number;
    drafts_today: number;
    tokens_used: number;
  };
  recent_activity: Array<{
    type: string;
    description: string;
    timestamp: string;
  }>;
}

export const analyticsApi = {
  getDashboard: async (): Promise<DashboardMetrics> => {
    const { data } = await api.get("/analytics/dashboard");
    return data;
  },

  getRfpAnalytics: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<{
    by_date: Array<{ date: string; count: number }>;
    by_naics: Record<string, number>;
    by_set_aside: Record<string, number>;
    avg_value: number;
  }> => {
    const { data } = await api.get("/analytics/rfps", { params });
    return data;
  },

  getProposalAnalytics: async (): Promise<{
    completion_rates: Array<{ month: string; rate: number }>;
    avg_sections_per_proposal: number;
    top_templates: Array<{ name: string; usage: number }>;
  }> => {
    const { data } = await api.get("/analytics/proposals");
    return data;
  },

  getAiUsage: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<{
    by_date: Array<{ date: string; calls: number; tokens: number }>;
    total_calls: number;
    total_tokens: number;
    cost_estimate: number;
  }> => {
    const { data } = await api.get("/analytics/ai-usage", { params });
    return data;
  },

  getObservability: async (params?: { days?: number }): Promise<ObservabilityMetrics> => {
    const { data } = await api.get("/analytics/observability", { params });
    return data;
  },
};

// =============================================================================
// Audit Endpoints
// =============================================================================

export const auditApi = {
  list: async (params?: {
    entity_type?: string;
    action?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  }): Promise<AuditEvent[]> => {
    const { data } = await api.get("/audit", { params });
    return data;
  },

  summary: async (params?: { days?: number }): Promise<AuditSummary> => {
    const { data } = await api.get("/audit/summary", { params });
    return data;
  },
};

// =============================================================================
// Notification Endpoints
// =============================================================================

export interface Notification {
  id: number;
  type: string;
  title: string;
  message: string;
  data: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}

export interface NotificationPreferences {
  email_enabled: boolean;
  slack_enabled: boolean;
  deadline_reminder_days: number[];
  notify_on_analysis_complete: boolean;
  notify_on_draft_complete: boolean;
  daily_digest: boolean;
}

export const notificationApi = {
  list: async (params?: {
    unread_only?: boolean;
    limit?: number;
  }): Promise<Notification[]> => {
    const { data } = await api.get("/notifications", { params });
    return data;
  },

  markAsRead: async (notificationId: number): Promise<void> => {
    await api.post(`/notifications/${notificationId}/read`);
  },

  markAllAsRead: async (): Promise<void> => {
    await api.post("/notifications/read-all");
  },

  getPreferences: async (): Promise<NotificationPreferences> => {
    const { data } = await api.get("/notifications/preferences");
    return data;
  },

  updatePreferences: async (
    prefs: Partial<NotificationPreferences>
  ): Promise<NotificationPreferences> => {
    const { data } = await api.put("/notifications/preferences", prefs);
    return data;
  },

  getUpcomingDeadlines: async (days?: number): Promise<
    Array<{
      rfp_id: number;
      title: string;
      deadline: string;
      days_remaining: number;
    }>
  > => {
    const { data } = await api.get("/notifications/deadlines", {
      params: { days },
    });
    return data;
  },
};

// =============================================================================
// Team Endpoints
// =============================================================================

export type TeamRole = "owner" | "admin" | "member" | "viewer";

export interface Team {
  id: number;
  name: string;
  description: string | null;
  owner_id: number;
  member_count: number;
  your_role: TeamRole;
  created_at: string;
}

export interface TeamMember {
  user_id: number;
  email: string;
  full_name: string | null;
  role: TeamRole;
  joined_at: string | null;
}

export interface Comment {
  id: number;
  content: string;
  user_id: number;
  user_name: string;
  parent_id: number | null;
  is_resolved: boolean;
  created_at: string;
}

export const teamApi = {
  list: async (): Promise<Team[]> => {
    const { data } = await api.get("/teams");
    return data;
  },

  create: async (team: {
    name: string;
    description?: string;
  }): Promise<Team> => {
    const { data } = await api.post("/teams", team);
    return data;
  },

  get: async (
    teamId: number
  ): Promise<Team & { members: TeamMember[] }> => {
    const { data } = await api.get(`/teams/${teamId}`);
    return data;
  },

  invite: async (
    teamId: number,
    email: string,
    role: TeamRole = "member"
  ): Promise<{ message: string; invitation_token?: string }> => {
    const { data } = await api.post(`/teams/${teamId}/invite`, { email, role });
    return data;
  },

  removeMember: async (teamId: number, userId: number): Promise<void> => {
    await api.delete(`/teams/${teamId}/members/${userId}`);
  },

  updateMemberRole: async (
    teamId: number,
    userId: number,
    role: TeamRole
  ): Promise<{ message: string; user_id: number; role: TeamRole }> => {
    const { data } = await api.patch(`/teams/${teamId}/members/${userId}`, {
      role,
    });
    return data;
  },

  // Comments
  getComments: async (
    proposalId: number,
    sectionId: number
  ): Promise<Comment[]> => {
    const { data } = await api.get(
      `/teams/proposals/${proposalId}/sections/${sectionId}/comments`
    );
    return data;
  },

  addComment: async (
    proposalId: number,
    sectionId: number,
    content: string,
    parentId?: number
  ): Promise<Comment> => {
    const { data } = await api.post(
      `/teams/proposals/${proposalId}/sections/${sectionId}/comments`,
      { content, parent_id: parentId }
    );
    return data;
  },

  resolveComment: async (commentId: number): Promise<void> => {
    await api.post(`/teams/comments/${commentId}/resolve`);
  },
};

// =============================================================================
// WebSocket Utilities
// =============================================================================

export const createWebSocket = (token: string): WebSocket => {
  const wsUrl = API_BASE_URL.replace(/^http/, "ws");
  return new WebSocket(`${wsUrl}/ws?token=${token}`);
};

export const useTaskWebSocket = (
  taskId: string,
  onUpdate: (status: TaskStatus) => void
): (() => void) => {
  const token = tokenManager.getAccessToken();
  if (!token) {
    console.error("No auth token available for WebSocket");
    return () => {};
  }

  const ws = createWebSocket(token);

  ws.onopen = () => {
    ws.send(JSON.stringify({ action: "watch", task_id: taskId }));
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "task_update" && data.task_id === taskId) {
        onUpdate(data.status);
      }
    } catch (e) {
      console.error("WebSocket message parse error:", e);
    }
  };

  ws.onerror = (error) => {
    console.error("WebSocket error:", error);
  };

  // Return cleanup function
  return () => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: "unwatch", task_id: taskId }));
    }
    ws.close();
  };
};

// =============================================================================
// Version History Endpoints
// =============================================================================

export interface ProposalVersion {
  id: number;
  proposal_id: number;
  version_number: number;
  version_type: string;
  description: string;
  user_id: number;
  created_at: string;
  has_snapshot: boolean;
}

export interface SectionVersion {
  id: number;
  section_id: number;
  version_number: number;
  change_type: string;
  change_summary: string | null;
  word_count: number;
  created_at: string;
}

export interface VersionDetail {
  id: number;
  version_number: number;
  change_type: string;
  content: string;
  word_count: number;
  created_at: string;
  diff_from_previous: string | null;
}

export const versionApi = {
  // Proposal versions
  listProposalVersions: async (
    proposalId: number,
    params?: { limit?: number; offset?: number }
  ): Promise<ProposalVersion[]> => {
    const { data } = await api.get(`/versions/proposals/${proposalId}`, {
      params,
    });
    return data;
  },

  getProposalVersion: async (
    proposalId: number,
    versionId: number
  ): Promise<ProposalVersion & { snapshot: Record<string, unknown> }> => {
    const { data } = await api.get(
      `/versions/proposals/${proposalId}/version/${versionId}`
    );
    return data;
  },

  // Section versions
  listSectionVersions: async (
    sectionId: number,
    params?: { limit?: number }
  ): Promise<SectionVersion[]> => {
    const { data } = await api.get(`/versions/sections/${sectionId}`, {
      params,
    });
    return data;
  },

  getSectionVersion: async (
    sectionId: number,
    versionId: number
  ): Promise<VersionDetail> => {
    const { data } = await api.get(
      `/versions/sections/${sectionId}/version/${versionId}`
    );
    return data;
  },

  restoreSection: async (
    sectionId: number,
    versionId: number
  ): Promise<{ message: string; section_id: number; restored_version: number }> => {
    const { data } = await api.post(`/versions/sections/${sectionId}/restore`, {
      version_id: versionId,
    });
    return data;
  },

  compareSectionVersions: async (
    sectionId: number,
    versionA: number,
    versionB: number
  ): Promise<{
    section_id: number;
    version_a: { version_number: number; content: string; word_count: number; created_at: string };
    version_b: { version_number: number; content: string; word_count: number; created_at: string };
  }> => {
    const { data } = await api.get(`/versions/sections/${sectionId}/compare`, {
      params: { version_a: versionA, version_b: versionB },
    });
    return data;
  },
};

// =============================================================================
// Health Endpoints
// =============================================================================

export const healthApi = {
  check: async (): Promise<{ status: string }> => {
    const { data } = await api.get("/health");
    return data;
  },

  ready: async (): Promise<{
    status: string;
    checks: Record<string, boolean | string>;
  }> => {
    const { data } = await api.get("/health/ready");
    return data;
  },
};

export default api;
