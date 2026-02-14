import api from "./client";
import type {
  MarketSignal,
  SignalListResponse,
  SignalCreatePayload,
  SignalSubscription,
  SubscriptionPayload,
  SignalType,
  SignalDigestPreview,
  SignalDigestSendResponse,
  SignalIngestResponse,
  SignalRescoreResponse,
} from "@/types/signals";

export const signalApi = {
  feed: async (params?: {
    signal_type?: SignalType;
    agency?: string;
    unread_only?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<SignalListResponse> => {
    const { data } = await api.get("/signals/feed", { params });
    return data;
  },

  list: async (): Promise<MarketSignal[]> => {
    const { data } = await api.get("/signals");
    return data;
  },

  create: async (payload: SignalCreatePayload): Promise<MarketSignal> => {
    const { data } = await api.post("/signals", payload);
    return data;
  },

  markRead: async (signalId: number): Promise<void> => {
    await api.patch(`/signals/${signalId}/read`);
  },

  delete: async (signalId: number): Promise<void> => {
    await api.delete(`/signals/${signalId}`);
  },

  getSubscription: async (): Promise<SignalSubscription | null> => {
    const { data } = await api.get("/signals/subscription");
    return data;
  },

  upsertSubscription: async (
    payload: SubscriptionPayload
  ): Promise<SignalSubscription> => {
    const { data } = await api.post("/signals/subscription", payload);
    return data;
  },

  ingestNews: async (params?: {
    max_items_per_source?: number;
    use_fallback_only?: boolean;
  }): Promise<SignalIngestResponse> => {
    const { data } = await api.post("/signals/ingest/news", null, { params });
    return data;
  },

  ingestBudgetAnalysis: async (params?: { limit?: number }): Promise<SignalIngestResponse> => {
    const { data } = await api.post("/signals/ingest/budget-analysis", null, { params });
    return data;
  },

  rescore: async (params?: { unread_only?: boolean }): Promise<SignalRescoreResponse> => {
    const { data } = await api.post("/signals/rescore", null, { params });
    return data;
  },

  digestPreview: async (params?: {
    period_days?: number;
    limit?: number;
  }): Promise<SignalDigestPreview> => {
    const { data } = await api.get("/signals/digest-preview", { params });
    return data;
  },

  sendDigest: async (params?: {
    period_days?: number;
    limit?: number;
  }): Promise<SignalDigestSendResponse> => {
    const { data } = await api.post("/signals/digest-send", null, { params });
    return data;
  },
};
