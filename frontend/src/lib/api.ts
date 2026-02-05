import axios from "axios";
import type {
  RFP,
  RFPListItem,
  ComplianceMatrix,
  Proposal,
  ProposalSection,
  KnowledgeBaseDocument,
  CapturePlan,
  CapturePlanListItem,
  CaptureStage,
  BidDecision,
  GateReview,
  TeamingPartner,
  TeamingPartnerLink,
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

  triggerKillerFilter: async (rfpId: number): Promise<TaskResponse> => {
    const { data } = await api.post(`/analyze/${rfpId}/filter`);
    return data;
  },
};

// =============================================================================
// Draft Generation Endpoints
// =============================================================================

export const draftApi = {
  createProposal: async (
    rfpId: number,
    title: string
  ): Promise<Proposal> => {
    const { data } = await api.post("/draft/proposals", { rfp_id: rfpId, title });
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
