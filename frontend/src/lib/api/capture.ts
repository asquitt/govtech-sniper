import api from "./client";
import type {
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
  BudgetIntelligence,
  BidScenarioRequest,
  BidScenarioSimulationResponse,
} from "@/types";

// =============================================================================
// Bid Decision Response Types
// =============================================================================

interface BidScorecardResponse {
  id: number;
  rfp_id: number;
  overall_score: number | null;
  recommendation: string | null;
  confidence?: number | null;
  criteria_scores?: { name: string; weight: number; score: number; reasoning?: string }[];
  reasoning?: string | null;
  scorer_type?: string;
  scorer_id?: number | null;
  win_probability?: number | null;
}

interface BidScorecardListItem {
  id: number;
  rfp_id: number;
  overall_score: number | null;
  recommendation: string | null;
  confidence: number | null;
  reasoning: string | null;
  scorer_type: string;
  scorer_id: number | null;
  criteria_scores: { name: string; weight: number; score: number; reasoning?: string }[];
  created_at: string;
}

interface BidDecisionSummaryResponse {
  rfp_id: number;
  total_votes: number;
  ai_score: number | null;
  human_avg: number | null;
  overall_recommendation: string | null;
  bid_count: number;
  no_bid_count: number;
  conditional_count: number;
}

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

  // Bid Decision
  aiEvaluateBid: async (rfpId: number): Promise<BidScorecardResponse> => {
    const { data } = await api.post(`/capture/scorecards/${rfpId}/ai-evaluate`);
    return data;
  },

  submitHumanVote: async (
    rfpId: number,
    payload: {
      criteria_scores: { name: string; weight: number; score: number; reasoning?: string }[];
      overall_score: number;
      recommendation: "bid" | "no_bid" | "conditional";
      reasoning?: string;
    }
  ): Promise<BidScorecardResponse> => {
    const { data } = await api.post(`/capture/scorecards/${rfpId}/vote`, payload);
    return data;
  },

  listScorecards: async (rfpId: number): Promise<BidScorecardListItem[]> => {
    const { data } = await api.get(`/capture/scorecards/${rfpId}`);
    return data;
  },

  getBidSummary: async (rfpId: number): Promise<BidDecisionSummaryResponse> => {
    const { data } = await api.get(`/capture/scorecards/${rfpId}/summary`);
    return data;
  },

  simulateBidScenarios: async (
    rfpId: number,
    payload?: { scenarios?: BidScenarioRequest[] }
  ): Promise<BidScenarioSimulationResponse> => {
    const { data } = await api.post(`/capture/scorecards/${rfpId}/scenario-simulator`, payload ?? {});
    return data;
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
