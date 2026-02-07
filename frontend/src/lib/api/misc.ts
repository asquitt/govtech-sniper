import api from "./client";
import type {
  AwardRecord,
  OpportunityContact,
  ExtractedContact,
  AgencyProfile,
  WordAddinSession,
  WordAddinSessionStatus,
  WordAddinEvent,
  ProposalGraphicRequest,
  GraphicsRequestStatus,
  AuditEvent,
  AuditSummary,
  ObservabilityMetrics,
  WinRateData,
  PipelineByStageData,
  ConversionRatesData,
  ProposalTurnaroundData,
  NAICSPerformanceData,
} from "@/types";

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

  extract: async (rfpId: number): Promise<ExtractedContact[]> => {
    const { data } = await api.post(`/contacts/extract/${rfpId}`);
    return data;
  },

  search: async (params?: {
    agency?: string;
    role?: string;
    location?: string;
    name?: string;
    limit?: number;
  }): Promise<OpportunityContact[]> => {
    const { data } = await api.get("/contacts/search", { params });
    return data;
  },

  listAgencies: async (): Promise<AgencyProfile[]> => {
    const { data } = await api.get("/contacts/agencies");
    return data;
  },

  upsertAgency: async (payload: {
    agency_name: string;
    office?: string;
    address?: string;
    website?: string;
    primary_contact_id?: number;
  }): Promise<AgencyProfile> => {
    const { data } = await api.post("/contacts/agencies", payload);
    return data;
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

  getWinRate: async (): Promise<WinRateData> => {
    const { data } = await api.get("/analytics/win-rate");
    return data;
  },

  getPipelineByStage: async (): Promise<PipelineByStageData> => {
    const { data } = await api.get("/analytics/pipeline-by-stage");
    return data;
  },

  getConversionRates: async (): Promise<ConversionRatesData> => {
    const { data } = await api.get("/analytics/conversion-rates");
    return data;
  },

  getProposalTurnaround: async (): Promise<ProposalTurnaroundData> => {
    const { data } = await api.get("/analytics/proposal-turnaround");
    return data;
  },

  getNaicsPerformance: async (): Promise<NAICSPerformanceData> => {
    const { data } = await api.get("/analytics/naics-performance");
    return data;
  },

  exportReport: async (reportType: string, format: string = "csv"): Promise<string> => {
    const { data } = await api.post("/analytics/export", { report_type: reportType, format }, {
      responseType: "text",
      headers: { Accept: "text/csv" },
    });
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
