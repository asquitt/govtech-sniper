import api from "./client";
import type {
  CapabilityGapResult,
  TeamingPartnerCohortDrilldownResponse,
  TeamingDigestPreview,
  TeamingDigestSchedule,
  TeamingNDA,
  TeamingPartnerPublicProfile,
  TeamingPartnerTrendDrilldownResponse,
  TeamingPerformanceRating,
  TeamingRequest,
  TeamingRequestTrend,
} from "@/types";

export const teamingBoardApi = {
  searchPartners: async (params?: {
    naics?: string;
    set_aside?: string;
    capability?: string;
    clearance?: string;
    q?: string;
  }): Promise<TeamingPartnerPublicProfile[]> => {
    const { data } = await api.get("/teaming/search", { params });
    return data;
  },

  getProfile: async (partnerId: number): Promise<TeamingPartnerPublicProfile> => {
    const { data } = await api.get(`/teaming/profile/${partnerId}`);
    return data;
  },

  sendRequest: async (payload: {
    to_partner_id: number;
    rfp_id?: number;
    message?: string;
  }): Promise<TeamingRequest> => {
    const { data } = await api.post("/teaming/requests", payload);
    return data;
  },

  listRequests: async (direction: "sent" | "received" = "sent"): Promise<TeamingRequest[]> => {
    const { data } = await api.get("/teaming/requests", { params: { direction } });
    return data;
  },

  updateRequest: async (requestId: number, status: "accepted" | "declined"): Promise<TeamingRequest> => {
    const { data } = await api.patch(`/teaming/requests/${requestId}`, { status });
    return data;
  },

  getRequestFitTrends: async (days = 30): Promise<TeamingRequestTrend> => {
    const { data } = await api.get("/teaming/requests/fit-trends", {
      params: { days },
    });
    return data;
  },

  getPartnerTrends: async (
    days = 30
  ): Promise<TeamingPartnerTrendDrilldownResponse> => {
    const { data } = await api.get("/teaming/requests/partner-trends", {
      params: { days },
    });
    return data;
  },

  getPartnerCohorts: async (
    days = 30,
    topN = 8
  ): Promise<TeamingPartnerCohortDrilldownResponse> => {
    const { data } = await api.get("/teaming/requests/partner-cohorts", {
      params: { days, top_n: topN },
    });
    return data;
  },

  getDigestSchedule: async (): Promise<TeamingDigestSchedule> => {
    const { data } = await api.get("/teaming/digest-schedule");
    return data;
  },

  updateDigestSchedule: async (
    payload: Partial<{
      frequency: "daily" | "weekly";
      day_of_week: number | null;
      hour_utc: number;
      minute_utc: number;
      channel: "in_app" | "email";
      include_declined_reasons: boolean;
      is_enabled: boolean;
    }>
  ): Promise<TeamingDigestSchedule> => {
    const { data } = await api.patch("/teaming/digest-schedule", payload);
    return data;
  },

  sendDigest: async (days = 30): Promise<TeamingDigestPreview> => {
    const { data } = await api.post("/teaming/digest-send", null, {
      params: { days },
    });
    return data;
  },

  exportRequestAuditCsv: async (
    direction: "sent" | "received" | "all" = "all",
    days = 30
  ): Promise<Blob> => {
    const { data } = await api.get("/teaming/requests/audit-export", {
      params: { direction, days },
      responseType: "blob",
      headers: { Accept: "text/csv" },
    });
    return data;
  },

  getGapAnalysis: async (rfpId: number): Promise<CapabilityGapResult> => {
    const { data } = await api.get(`/teaming/gap-analysis/${rfpId}`);
    return data;
  },

  // NDA Tracking
  createNDA: async (payload: {
    partner_id: number;
    rfp_id?: number;
    signed_date?: string;
    expiry_date?: string;
    document_path?: string;
    notes?: string;
  }): Promise<TeamingNDA> => {
    const { data } = await api.post("/teaming/ndas", payload);
    return data;
  },

  listNDAs: async (params?: {
    partner_id?: number;
    status?: string;
  }): Promise<TeamingNDA[]> => {
    const { data } = await api.get("/teaming/ndas", { params });
    return data;
  },

  updateNDA: async (
    ndaId: number,
    payload: {
      status?: string;
      signed_date?: string;
      expiry_date?: string;
      document_path?: string;
      notes?: string;
    },
  ): Promise<TeamingNDA> => {
    const { data } = await api.patch(`/teaming/ndas/${ndaId}`, payload);
    return data;
  },

  // Performance Ratings
  createRating: async (payload: {
    partner_id: number;
    rfp_id?: number;
    rating: number;
    responsiveness?: number;
    quality?: number;
    timeliness?: number;
    comment?: string;
  }): Promise<TeamingPerformanceRating> => {
    const { data } = await api.post("/teaming/ratings", payload);
    return data;
  },

  listPartnerRatings: async (partnerId: number): Promise<TeamingPerformanceRating[]> => {
    const { data } = await api.get(`/teaming/partners/${partnerId}/ratings`);
    return data;
  },
};
