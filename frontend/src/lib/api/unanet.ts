import api from "./client";
import type { UnanetStatus, UnanetProject, UnanetSyncResult } from "@/types";

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
};
