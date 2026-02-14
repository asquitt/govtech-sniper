import api from "./client";
import type {
  EventAlertResponse,
  EventIngestResponse,
  IndustryEvent,
} from "@/types";

export const eventApi = {
  list: async (archived = false): Promise<IndustryEvent[]> => {
    const { data } = await api.get("/events", { params: { archived } });
    return data;
  },

  upcoming: async (): Promise<IndustryEvent[]> => {
    const { data } = await api.get("/events/upcoming");
    return data;
  },

  calendar: async (month: number, year: number): Promise<IndustryEvent[]> => {
    const { data } = await api.get("/events/calendar", {
      params: { month, year },
    });
    return data;
  },

  ingest: async (params?: {
    days_ahead?: number;
    include_curated?: boolean;
  }): Promise<EventIngestResponse> => {
    const { data } = await api.post("/events/ingest", null, { params });
    return data;
  },

  alerts: async (params?: {
    days?: number;
    min_score?: number;
    limit?: number;
  }): Promise<EventAlertResponse> => {
    const { data } = await api.get("/events/alerts", { params });
    return data;
  },

  get: async (id: number): Promise<IndustryEvent> => {
    const { data } = await api.get(`/events/${id}`);
    return data;
  },

  create: async (payload: {
    title: string;
    date: string;
    agency?: string;
    event_type?: string;
    location?: string;
    registration_url?: string;
    related_rfp_id?: number;
    description?: string;
    source?: string;
  }): Promise<IndustryEvent> => {
    const { data } = await api.post("/events", payload);
    return data;
  },

  update: async (
    id: number,
    payload: Partial<IndustryEvent>
  ): Promise<IndustryEvent> => {
    const { data } = await api.patch(`/events/${id}`, payload);
    return data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/events/${id}`);
  },
};
