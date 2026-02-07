import api from "./client";
import type {
  MarketSignal,
  SignalListResponse,
  SignalCreatePayload,
  SignalSubscription,
  SubscriptionPayload,
  SignalType,
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
};
