import { create } from "zustand";
import { dashApi } from "@/lib/api";
import type { DashSession } from "@/types";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Record<string, unknown>[];
  isStreaming?: boolean;
}

interface DashState {
  sessions: DashSession[];
  activeSessionId: number | null;
  messages: ChatMessage[];
  selectedRfpId: number | null;
  isLoading: boolean;
  error: string | null;
  abortController: AbortController | null;

  // Actions
  loadSessions: () => Promise<void>;
  createSession: () => Promise<number>;
  selectSession: (id: number) => Promise<void>;
  deleteSession: (id: number) => Promise<void>;
  sendMessage: (question: string) => Promise<void>;
  stopStreaming: () => void;
  setSelectedRfpId: (id: number | null) => void;
  setError: (error: string | null) => void;
}

export const useDashStore = create<DashState>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: [],
  selectedRfpId: null,
  isLoading: false,
  error: null,
  abortController: null,

  loadSessions: async () => {
    try {
      const sessions = await dashApi.listSessions();
      set({ sessions });
      // Auto-select most recent if none selected
      if (!get().activeSessionId && sessions.length > 0) {
        await get().selectSession(sessions[0].id);
      }
    } catch (err) {
      console.error("Failed to load sessions", err);
    }
  },

  createSession: async () => {
    const session = await dashApi.createSession();
    set((s) => ({
      sessions: [session, ...s.sessions],
      activeSessionId: session.id,
      messages: [],
    }));
    return session.id;
  },

  selectSession: async (id: number) => {
    set({ activeSessionId: id, messages: [], isLoading: true });
    try {
      const dbMessages = await dashApi.getSessionMessages(id);
      const messages: ChatMessage[] = dbMessages
        .filter((m) => m.role !== "system")
        .map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
          citations: m.citations,
        }));
      set({ messages, isLoading: false });
    } catch (err) {
      console.error("Failed to load messages", err);
      set({ isLoading: false });
    }
  },

  deleteSession: async (id: number) => {
    await dashApi.deleteSession(id);
    const { sessions, activeSessionId } = get();
    const remaining = sessions.filter((s) => s.id !== id);
    set({ sessions: remaining });
    if (activeSessionId === id) {
      if (remaining.length > 0) {
        await get().selectSession(remaining[0].id);
      } else {
        set({ activeSessionId: null, messages: [] });
      }
    }
  },

  sendMessage: async (question: string) => {
    const state = get();
    if (state.isLoading) return;

    // Create session if needed
    let sessionId = state.activeSessionId;
    if (!sessionId) {
      sessionId = await get().createSession();
    }

    set((s) => ({
      isLoading: true,
      error: null,
      messages: [...s.messages, { role: "user", content: question }],
    }));

    // Add empty streaming assistant message
    set((s) => ({
      messages: [...s.messages, { role: "assistant", content: "", isStreaming: true }],
    }));

    const abortController = new AbortController();
    set({ abortController });

    try {
      await dashApi.streamChat(
        {
          question,
          rfp_id: state.selectedRfpId ?? undefined,
          session_id: sessionId,
        },
        {
          onChunk: (content) => {
            set((s) => {
              const msgs = [...s.messages];
              const last = msgs[msgs.length - 1];
              if (last?.role === "assistant") {
                msgs[msgs.length - 1] = { ...last, content: last.content + content };
              }
              return { messages: msgs };
            });
          },
          onDone: (data) => {
            set((s) => {
              const msgs = [...s.messages];
              const last = msgs[msgs.length - 1];
              if (last?.role === "assistant") {
                msgs[msgs.length - 1] = {
                  ...last,
                  content: data.full_text || last.content,
                  citations: data.citations,
                  isStreaming: false,
                };
              }
              // Update session title in list (may have been auto-set)
              const sessions = s.sessions.map((sess) =>
                sess.id === sessionId && !sess.title
                  ? { ...sess, title: question.slice(0, 80) }
                  : sess
              );
              return { messages: msgs, sessions, isLoading: false, abortController: null };
            });
          },
          onError: (error) => {
            set((s) => {
              const msgs = [...s.messages];
              const last = msgs[msgs.length - 1];
              if (last?.role === "assistant" && last.isStreaming) {
                msgs[msgs.length - 1] = {
                  ...last,
                  content: last.content || `Error: ${error.message}`,
                  isStreaming: false,
                };
              }
              return { messages: msgs, isLoading: false, error: error.message, abortController: null };
            });
          },
          signal: abortController.signal,
        }
      );
    } catch (err) {
      set({ isLoading: false, abortController: null });
    }
  },

  stopStreaming: () => {
    const { abortController } = get();
    if (abortController) {
      abortController.abort();
      set((s) => {
        const msgs = [...s.messages];
        const last = msgs[msgs.length - 1];
        if (last?.role === "assistant" && last.isStreaming) {
          msgs[msgs.length - 1] = { ...last, isStreaming: false };
        }
        return { messages: msgs, isLoading: false, abortController: null };
      });
    }
  },

  setSelectedRfpId: (id) => set({ selectedRfpId: id }),
  setError: (error) => set({ error }),
}));
