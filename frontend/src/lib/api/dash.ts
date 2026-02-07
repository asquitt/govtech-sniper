import api from "./client";
import type { DashSession, DashMessage } from "@/types";

// =============================================================================
// Dash Endpoints
// =============================================================================

export const dashApi = {
  listSessions: async (): Promise<DashSession[]> => {
    const { data } = await api.get("/dash/sessions");
    return data;
  },

  createSession: async (title?: string): Promise<DashSession> => {
    const { data } = await api.post("/dash/sessions", { title });
    return data;
  },

  addMessage: async (
    sessionId: number,
    payload: { role: "user" | "assistant"; content: string }
  ): Promise<DashMessage> => {
    const { data } = await api.post(`/dash/sessions/${sessionId}/messages`, payload);
    return data;
  },

  ask: async (payload: {
    question: string;
    rfp_id?: number;
  }): Promise<{ answer: string; citations: Record<string, unknown>[] }> => {
    const { data } = await api.post("/dash/ask", payload);
    return data;
  },
};
