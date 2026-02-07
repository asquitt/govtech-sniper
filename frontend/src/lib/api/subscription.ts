import api from "./client";
import type {
  PlanDefinition,
  UsageStats,
  CheckoutSessionResponse,
  SubscriptionStatus,
  PortalResponse,
} from "@/types";

// =============================================================================
// Subscription Endpoints
// =============================================================================

export const subscriptionApi = {
  listPlans: async (): Promise<PlanDefinition[]> => {
    const { data } = await api.get("/subscription/plans");
    return data;
  },

  currentPlan: async (): Promise<PlanDefinition> => {
    const { data } = await api.get("/subscription/current");
    return data;
  },

  usage: async (): Promise<UsageStats> => {
    const { data } = await api.get("/subscription/usage");
    return data;
  },

  status: async (): Promise<SubscriptionStatus> => {
    const { data } = await api.get("/subscription/status");
    return data;
  },

  checkout: async (
    tier: string,
    annual: boolean = false
  ): Promise<CheckoutSessionResponse> => {
    const { data } = await api.post("/subscription/checkout", null, {
      params: { tier, annual },
    });
    return data;
  },

  portal: async (): Promise<PortalResponse> => {
    const { data } = await api.post("/subscription/portal");
    return data;
  },
};
