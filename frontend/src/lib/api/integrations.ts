import api from "./client";
import type {
  IntegrationConfig,
  IntegrationProvider,
  IntegrationProviderDefinition,
  IntegrationTestResult,
  IntegrationSyncRun,
  IntegrationWebhookEvent,
  IntegrationSsoAuthorizeResponse,
} from "@/types";

// =============================================================================
// Integration Endpoints
// =============================================================================

export const integrationApi = {
  providers: async (): Promise<IntegrationProviderDefinition[]> => {
    const { data } = await api.get("/integrations/providers");
    return data;
  },

  list: async (params?: { provider?: IntegrationProvider }): Promise<IntegrationConfig[]> => {
    const { data } = await api.get("/integrations", { params });
    return data;
  },

  create: async (payload: {
    provider: IntegrationProvider;
    name?: string | null;
    is_enabled?: boolean;
    config?: Record<string, unknown>;
  }): Promise<IntegrationConfig> => {
    const { data } = await api.post("/integrations", payload);
    return data;
  },

  update: async (
    integrationId: number,
    payload: Partial<{
      name: string | null;
      is_enabled: boolean;
      config: Record<string, unknown>;
    }>
  ): Promise<IntegrationConfig> => {
    const { data } = await api.patch(`/integrations/${integrationId}`, payload);
    return data;
  },

  remove: async (integrationId: number): Promise<void> => {
    await api.delete(`/integrations/${integrationId}`);
  },

  test: async (integrationId: number): Promise<IntegrationTestResult> => {
    const { data } = await api.post(`/integrations/${integrationId}/test`, {});
    return data;
  },

  authorizeSso: async (integrationId: number): Promise<IntegrationSsoAuthorizeResponse> => {
    const { data } = await api.post(`/integrations/${integrationId}/sso/authorize`, {});
    return data;
  },

  ssoCallback: async (integrationId: number, code: string): Promise<{ status: string }> => {
    const { data } = await api.post(`/integrations/${integrationId}/sso/callback`, { code });
    return data;
  },

  sync: async (integrationId: number): Promise<IntegrationSyncRun> => {
    const { data } = await api.post(`/integrations/${integrationId}/sync`, {});
    return data;
  },

  syncs: async (integrationId: number): Promise<IntegrationSyncRun[]> => {
    const { data } = await api.get(`/integrations/${integrationId}/syncs`);
    return data;
  },

  sendWebhook: async (
    integrationId: number,
    payload: Record<string, unknown>
  ): Promise<IntegrationWebhookEvent> => {
    const { data } = await api.post(`/integrations/${integrationId}/webhook`, payload);
    return data;
  },

  listWebhooks: async (integrationId: number): Promise<IntegrationWebhookEvent[]> => {
    const { data } = await api.get(`/integrations/${integrationId}/webhooks`);
    return data;
  },
};
