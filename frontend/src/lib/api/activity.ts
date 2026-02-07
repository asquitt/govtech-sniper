import api from "./client";
import type { ActivityFeedEntry, ActivityType } from "@/types";

export const activityApi = {
  list: async (
    proposalId: number,
    params?: { limit?: number; offset?: number; activity_type?: ActivityType }
  ): Promise<ActivityFeedEntry[]> => {
    const { data } = await api.get(`/activity/proposals/${proposalId}`, {
      params,
    });
    return data;
  },
};
