import api from "./client";
import type {
  SavedReport,
  SavedReportCreate,
  SavedReportUpdate,
  ReportDataResponse,
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

  setSchedule: async (id: number, frequency: ScheduleFrequency): Promise<SavedReport> => {
    const { data } = await api.post(`/reports/${id}/schedule`, null, {
      params: { frequency },
    });
    return data;
  },
};
