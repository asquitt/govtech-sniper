import api from "./client";
import type {
  SharePointSyncConfig,
  SharePointSyncLog,
  SyncDirection,
} from "@/types/sharepoint-sync";

export const sharepointSyncApi = {
  configure: async (payload: {
    proposal_id: number;
    sharepoint_folder: string;
    sync_direction?: SyncDirection;
    auto_sync_enabled?: boolean;
    watch_for_rfps?: boolean;
  }): Promise<SharePointSyncConfig> => {
    const { data } = await api.post("/sharepoint/sync/configure", payload);
    return data;
  },

  listConfigs: async (
    proposalId?: number
  ): Promise<SharePointSyncConfig[]> => {
    const { data } = await api.get("/sharepoint/sync/configs", {
      params: proposalId ? { proposal_id: proposalId } : undefined,
    });
    return data;
  },

  triggerSync: async (
    configId: number
  ): Promise<{ task_id: string; message: string; config_id: number }> => {
    const { data } = await api.post(`/sharepoint/sync/${configId}/trigger`);
    return data;
  },

  getSyncStatus: async (
    configId: number,
    limit?: number
  ): Promise<SharePointSyncLog[]> => {
    const { data } = await api.get(`/sharepoint/sync/${configId}/status`, {
      params: limit ? { limit } : undefined,
    });
    return data;
  },

  deleteConfig: async (configId: number): Promise<void> => {
    await api.delete(`/sharepoint/sync/${configId}`);
  },
};
