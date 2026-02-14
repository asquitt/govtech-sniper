import { api } from "./client";
import type {
  EmailIngestConfig,
  EmailIngestConfigCreate,
  EmailIngestSyncRequest,
  EmailIngestSyncResponse,
  EmailIngestConfigUpdate,
  IngestedEmail,
} from "@/types/email-ingest";

export const emailIngestApi = {
  createConfig: (data: EmailIngestConfigCreate) =>
    api.post<EmailIngestConfig>("/email-ingest/config", data).then((r) => r.data),

  listConfigs: () =>
    api.get<EmailIngestConfig[]>("/email-ingest/config").then((r) => r.data),

  updateConfig: (id: number, data: EmailIngestConfigUpdate) =>
    api.patch<EmailIngestConfig>(`/email-ingest/config/${id}`, data).then((r) => r.data),

  deleteConfig: (id: number) =>
    api.delete(`/email-ingest/config/${id}`).then((r) => r.data),

  testConnection: (id: number) =>
    api
      .post<{ success: boolean; message: string }>(`/email-ingest/config/${id}/test`)
      .then((r) => r.data),

  listHistory: (params?: {
    config_id?: number;
    status?: string;
    limit?: number;
    offset?: number;
  }) =>
    api
      .get<{ items: IngestedEmail[]; total: number }>("/email-ingest/history", {
        params,
      })
      .then((r) => r.data),

  reprocess: (emailId: number) =>
    api.post<IngestedEmail>(`/email-ingest/process/${emailId}`).then((r) => r.data),

  syncNow: (payload?: EmailIngestSyncRequest) =>
    api
      .post<EmailIngestSyncResponse>("/email-ingest/sync-now", payload ?? {})
      .then((r) => r.data),
};
