import api from "./client";
import type {
  WinLossAnalysis,
  BudgetIntelligenceData,
  PipelineForecast,
  KPIData,
  ResourceAllocation,
} from "@/types";

// =============================================================================
// Intelligence & Analytics Endpoints
// =============================================================================

export const intelligenceApi = {
  getWinLossAnalysis: async (): Promise<WinLossAnalysis> => {
    const { data } = await api.get("/intelligence/win-loss");
    return data;
  },

  getBudgetIntelligence: async (): Promise<BudgetIntelligenceData> => {
    const { data } = await api.get("/intelligence/budget");
    return data;
  },

  getPipelineForecast: async (
    granularity: "monthly" | "quarterly" = "quarterly"
  ): Promise<PipelineForecast> => {
    const { data } = await api.get("/intelligence/pipeline-forecast", {
      params: { granularity },
    });
    return data;
  },

  getKPIs: async (): Promise<KPIData> => {
    const { data } = await api.get("/intelligence/kpis");
    return data;
  },

  getResourceAllocation: async (): Promise<ResourceAllocation> => {
    const { data } = await api.get("/intelligence/resource-allocation");
    return data;
  },

  createDebrief: async (params: {
    capture_plan_id: number;
    outcome: string;
    source?: string;
    agency_feedback?: string;
    win_themes?: string[];
    loss_factors?: string[];
    winning_vendor?: string;
    winning_price?: number;
    our_price?: number;
    num_offerors?: number;
    technical_score?: number;
    management_score?: number;
    price_score?: number;
    past_performance_score?: number;
    lessons_learned?: string;
  }): Promise<{ id: number; status: string }> => {
    const { data } = await api.post("/intelligence/debriefs", null, {
      params,
    });
    return data;
  },
};
