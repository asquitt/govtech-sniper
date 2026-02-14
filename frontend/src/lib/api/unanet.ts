import api from "./client";
import type {
  UnanetFinancialRecord,
  UnanetFinancialSyncResult,
  UnanetProject,
  UnanetResource,
  UnanetResourceSyncResult,
  UnanetStatus,
  UnanetSyncResult,
} from "@/types";

// =============================================================================
// Unanet Endpoints
// =============================================================================

export const unanetApi = {
  getStatus: async (): Promise<UnanetStatus> => {
    const { data } = await api.get("/unanet/status");
    return data;
  },

  listProjects: async (): Promise<UnanetProject[]> => {
    const { data } = await api.get("/unanet/projects");
    return data;
  },

  sync: async (): Promise<UnanetSyncResult> => {
    const { data } = await api.post("/unanet/sync", {});
    return data;
  },

  listResources: async (): Promise<UnanetResource[]> => {
    const { data } = await api.get("/unanet/resources");
    return data;
  },

  listFinancials: async (): Promise<UnanetFinancialRecord[]> => {
    const { data } = await api.get("/unanet/financials");
    return data;
  },

  syncResources: async (): Promise<UnanetResourceSyncResult> => {
    const { data } = await api.post("/unanet/sync/resources", {});
    return data;
  },

  syncFinancials: async (): Promise<UnanetFinancialSyncResult> => {
    const { data } = await api.post("/unanet/sync/financials", {});
    return data;
  },
};
