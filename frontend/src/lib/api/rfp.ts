import api from "./client";
import type {
  RFP,
  RFPListItem,
  ComplianceMatrix,
  ComplianceRequirement,
  SavedSearch,
  SavedSearchRunResult,
  SAMSearchParams,
  TaskResponse,
  TaskStatus,
} from "@/types";

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
