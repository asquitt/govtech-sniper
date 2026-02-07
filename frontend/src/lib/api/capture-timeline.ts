import api from "./client";
import type { CaptureActivity, GanttPlanRow } from "@/types";

export const captureTimelineApi = {
  listActivities: async (planId: number): Promise<CaptureActivity[]> => {
    const { data } = await api.get(
      `/capture/timeline/${planId}/activities`
    );
    return data;
  },

  createActivity: async (
    planId: number,
    payload: {
      title: string;
      start_date?: string | null;
      end_date?: string | null;
      is_milestone?: boolean;
      status?: string;
      sort_order?: number;
      depends_on_id?: number | null;
    }
  ): Promise<CaptureActivity> => {
    const { data } = await api.post(
      `/capture/timeline/${planId}/activities`,
      payload
    );
    return data;
  },

  updateActivity: async (
    planId: number,
    activityId: number,
    payload: Partial<{
      title: string;
      start_date: string | null;
      end_date: string | null;
      is_milestone: boolean;
      status: string;
      sort_order: number;
      depends_on_id: number | null;
    }>
  ): Promise<CaptureActivity> => {
    const { data } = await api.patch(
      `/capture/timeline/${planId}/activities/${activityId}`,
      payload
    );
    return data;
  },

  deleteActivity: async (
    planId: number,
    activityId: number
  ): Promise<void> => {
    await api.delete(
      `/capture/timeline/${planId}/activities/${activityId}`
    );
  },

  getOverview: async (): Promise<GanttPlanRow[]> => {
    const { data } = await api.get("/capture/timeline/overview");
    return data;
  },
};
