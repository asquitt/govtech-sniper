import api from "./client";
import type {
  HelpArticle,
  InteractiveTutorial,
  SupportChatRequest,
  SupportChatResponse,
} from "@/types";

export const supportApi = {
  listArticles: async (params?: {
    q?: string;
    category?: string;
  }): Promise<HelpArticle[]> => {
    const { data } = await api.get("/support/help-center/articles", { params });
    return data;
  },

  getArticle: async (articleId: string): Promise<HelpArticle> => {
    const { data } = await api.get(`/support/help-center/articles/${articleId}`);
    return data;
  },

  listTutorials: async (params?: { feature?: string }): Promise<InteractiveTutorial[]> => {
    const { data } = await api.get("/support/tutorials", { params });
    return data;
  },

  getTutorial: async (tutorialId: string): Promise<InteractiveTutorial> => {
    const { data } = await api.get(`/support/tutorials/${tutorialId}`);
    return data;
  },

  chat: async (payload: SupportChatRequest): Promise<SupportChatResponse> => {
    const { data } = await api.post("/support/chat", payload);
    return data;
  },
};
