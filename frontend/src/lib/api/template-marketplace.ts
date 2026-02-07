import { api } from "./client";
import type {
  MarketplaceTemplate,
  TemplateRating,
} from "@/types/template-marketplace";

export const templateMarketplaceApi = {
  browse: (params?: {
    q?: string;
    category?: string;
    limit?: number;
    offset?: number;
  }) =>
    api.get<{ items: MarketplaceTemplate[]; total: number }>(
      "/templates/marketplace",
      { params }
    ),

  popular: () =>
    api.get<MarketplaceTemplate[]>("/templates/marketplace/popular"),

  publish: (id: number) =>
    api.post<MarketplaceTemplate>(`/templates/${id}/publish`),

  fork: (id: number) =>
    api.post<MarketplaceTemplate>(`/templates/${id}/fork`),

  rate: (id: number, data: TemplateRating) =>
    api.post(`/templates/${id}/rate`, data),
};
