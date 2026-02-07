import api from "./client";
import type { ProcurementForecast, ForecastAlert } from "@/types";

export const forecastApi = {
  list: async (): Promise<ProcurementForecast[]> => {
    const { data } = await api.get("/forecasts");
    return data;
  },

  create: async (payload: {
    title: string;
    agency?: string;
    naics_code?: string;
    estimated_value?: number;
    expected_solicitation_date?: string;
    expected_award_date?: string;
    fiscal_year?: number;
    source?: string;
    source_url?: string;
    description?: string;
  }): Promise<ProcurementForecast> => {
    const { data } = await api.post("/forecasts", payload);
    return data;
  },

  update: async (
    id: number,
    payload: Partial<ProcurementForecast>
  ): Promise<ProcurementForecast> => {
    const { data } = await api.patch(`/forecasts/${id}`, payload);
    return data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/forecasts/${id}`);
  },

  linkToRFP: async (
    forecastId: number,
    rfpId: number
  ): Promise<ProcurementForecast> => {
    const { data } = await api.post(
      `/forecasts/${forecastId}/link/${rfpId}`
    );
    return data;
  },

  runMatching: async (): Promise<{ new_alerts: number }> => {
    const { data } = await api.post("/forecasts/match");
    return data;
  },

  listAlerts: async (): Promise<ForecastAlert[]> => {
    const { data } = await api.get("/forecasts/alerts");
    return data;
  },

  dismissAlert: async (alertId: number): Promise<void> => {
    await api.patch(`/forecasts/alerts/${alertId}`);
  },
};
