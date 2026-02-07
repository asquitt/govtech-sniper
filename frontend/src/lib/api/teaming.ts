import api from "./client";
import type {
  TeamingPartnerPublicProfile,
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
};
