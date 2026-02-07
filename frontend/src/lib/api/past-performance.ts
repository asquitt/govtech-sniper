import { api } from "./client";
import type {
  PastPerformanceMetadata,
  PastPerformanceDocument,
  PastPerformanceListResponse,
  MatchResponse,
  NarrativeResponse,
} from "@/types/past-performance";

export const pastPerformanceApi = {
  addMetadata: (documentId: number, data: PastPerformanceMetadata) =>
    api.post<PastPerformanceDocument>(`/documents/${documentId}/past-performance-metadata`, data),

  list: () =>
    api.get<PastPerformanceListResponse>("/documents/past-performances"),

  match: (rfpId: number) =>
    api.post<MatchResponse>(`/documents/past-performances/match/${rfpId}`),

  generateNarrative: (documentId: number, rfpId: number) =>
    api.post<NarrativeResponse>(`/documents/past-performances/${documentId}/narrative/${rfpId}`),
};
