import api from "./client";
import { tokenManager } from "./client";
import type { DashSession, DashMessage } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

// =============================================================================
// Dash API
// =============================================================================

export const dashApi = {
  // Session management
  listSessions: async (): Promise<DashSession[]> => {
    const { data } = await api.get("/dash/sessions");
    return data;
  },

  createSession: async (title?: string): Promise<DashSession> => {
    const { data } = await api.post("/dash/sessions", { title });
    return data;
  },

  deleteSession: async (sessionId: number): Promise<void> => {
    await api.delete(`/dash/sessions/${sessionId}`);
  },

  getSessionMessages: async (sessionId: number): Promise<DashMessage[]> => {
    const { data } = await api.get(`/dash/sessions/${sessionId}/messages`);
    return data;
  },

  // Non-streaming ask
  ask: async (payload: {
    question: string;
    rfp_id?: number;
    session_id?: number;
  }): Promise<{ answer: string; citations: Record<string, unknown>[]; message_id?: number }> => {
    const { data } = await api.post("/dash/ask", payload);
    return data;
  },

  // Streaming chat via SSE (uses native fetch, not axios)
  streamChat: async (
    payload: { question: string; rfp_id?: number; session_id?: number },
    callbacks: {
      onChunk: (content: string) => void;
      onDone: (data: {
        citations: Record<string, unknown>[];
        message_id: number | null;
        full_text: string;
      }) => void;
      onError: (error: Error) => void;
      signal?: AbortSignal;
    }
  ): Promise<void> => {
    const token = tokenManager.getAccessToken();

    const response = await fetch(`${API_BASE_URL}/api/v1/dash/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
      signal: callbacks.signal,
    });

    if (!response.ok) {
      callbacks.onError(new Error(`HTTP ${response.status}: ${response.statusText}`));
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      callbacks.onError(new Error("No response body"));
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            // Next data line will have the payload
            continue;
          }
          if (line.startsWith("data: ")) {
            const jsonStr = line.slice(6);
            try {
              const parsed = JSON.parse(jsonStr);
              if (parsed.content !== undefined) {
                callbacks.onChunk(parsed.content);
              } else if (parsed.full_text !== undefined) {
                callbacks.onDone(parsed);
              }
            } catch {
              // Ignore malformed JSON lines
            }
          }
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return; // User cancelled
      }
      callbacks.onError(err instanceof Error ? err : new Error(String(err)));
    }
  },
};
