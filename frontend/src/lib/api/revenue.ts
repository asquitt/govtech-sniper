import api from "./client";
import type {
  PipelineSummaryResponse,
  RevenueTimelineResponse,
  AgencyRevenueResponse,
} from "@/types";

export const revenueApi = {
  getPipelineSummary: async (): Promise<PipelineSummaryResponse> => {
    const { data } = await api.get("/revenue/pipeline-summary");
    return data;
  },

  getTimeline: async (
    granularity: "monthly" | "quarterly" = "monthly"
  ): Promise<RevenueTimelineResponse> => {
    const { data } = await api.get("/revenue/timeline", {
      params: { granularity },
    });
    return data;
  },

  getByAgency: async (limit = 15): Promise<AgencyRevenueResponse> => {
    const { data } = await api.get("/revenue/by-agency", {
      params: { limit },
    });
    return data;
  },
};
