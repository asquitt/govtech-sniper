import api from "./client";
import type {
  CapabilityGapResult,
  TeamingNDA,
  TeamingPartnerPublicProfile,
  TeamingPerformanceRating,
  TeamingRequest,
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
