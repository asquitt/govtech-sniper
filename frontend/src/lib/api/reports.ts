import api from "./client";
import type {
  SavedReport,
  SavedReportCreate,
  SavedReportUpdate,
  ReportDataResponse,
  ReportDeliveryScheduleUpdate,
  ReportShareUpdate,
  ScheduleFrequency,
} from "@/types/report";

export const reportApi = {
  create: async (data: SavedReportCreate): Promise<SavedReport> => {
    const { data: result } = await api.post("/reports", data);
    return result;
  },

  list: async (): Promise<SavedReport[]> => {
    const { data } = await api.get("/reports");
    return data;
  },

  get: async (id: number): Promise<SavedReport> => {
    const { data } = await api.get(`/reports/${id}`);
    return data;
  },

  update: async (id: number, data: SavedReportUpdate): Promise<SavedReport> => {
    const { data: result } = await api.patch(`/reports/${id}`, data);
    return result;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/reports/${id}`);
  },

  generate: async (id: number): Promise<ReportDataResponse> => {
    const { data } = await api.post(`/reports/${id}/generate`);
    return data;
  },

  export: async (id: number): Promise<Blob> => {
    const { data } = await api.post(`/reports/${id}/export`, null, {
      responseType: "blob",
    });
    return data;
  },

  setSchedule: async (
    id: number,
    frequency: ScheduleFrequency,
    payload?: ReportDeliveryScheduleUpdate
  ): Promise<SavedReport> => {
    const { data } = await api.post(`/reports/${id}/schedule`, payload ?? null, {
      params: { frequency },
    });
    return data;
  },

  share: async (id: number, payload: ReportShareUpdate): Promise<SavedReport> => {
    const { data } = await api.patch(`/reports/${id}/share`, payload);
    return data;
  },

  getDelivery: async (id: number): Promise<{
    report_id: number;
    owner_email: string | null;
    frequency: ScheduleFrequency | null;
    enabled: boolean;
    recipients: string[];
    subject: string | null;
    last_delivered_at: string | null;
  }> => {
    const { data } = await api.get(`/reports/${id}/delivery`);
    return data;
  },

  sendDeliveryNow: async (id: number): Promise<{
    status: string;
    report_id: number;
    frequency: ScheduleFrequency;
    recipient_count: number;
    recipients: string[];
    row_count: number;
    subject: string;
    delivered_at: string;
  }> => {
    const { data } = await api.post(`/reports/${id}/delivery/send`);
    return data;
  },
};
