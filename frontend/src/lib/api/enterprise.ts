import api from "./client";
import type { SecretItem, WebhookDelivery, WebhookSubscription } from "@/types";

export const enterpriseApi = {
  listWebhooks: async (): Promise<WebhookSubscription[]> => {
    const { data } = await api.get("/webhooks");
    return data;
  },

  createWebhook: async (payload: {
    name: string;
    target_url: string;
    secret?: string | null;
    event_types?: string[];
    is_active?: boolean;
  }): Promise<WebhookSubscription> => {
    const { data } = await api.post("/webhooks", payload);
    return data;
  },

  updateWebhook: async (
    webhookId: number,
    payload: Partial<{
      name: string;
      target_url: string;
      secret: string | null;
      event_types: string[];
      is_active: boolean;
    }>
  ): Promise<WebhookSubscription> => {
    const { data } = await api.patch(`/webhooks/${webhookId}`, payload);
    return data;
  },

  deleteWebhook: async (webhookId: number): Promise<void> => {
    await api.delete(`/webhooks/${webhookId}`);
  },

  listWebhookDeliveries: async (webhookId: number): Promise<WebhookDelivery[]> => {
    const { data } = await api.get(`/webhooks/${webhookId}/deliveries`);
    return data;
  },

  listSecrets: async (): Promise<SecretItem[]> => {
    const { data } = await api.get("/secrets");
    return data;
  },

  createOrUpdateSecret: async (payload: {
    key: string;
    value: string;
  }): Promise<SecretItem> => {
    const { data } = await api.post("/secrets", payload);
    return data;
  },

  deleteSecret: async (secretKey: string): Promise<void> => {
    await api.delete(`/secrets/${encodeURIComponent(secretKey)}`);
  },
};
