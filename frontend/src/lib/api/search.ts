import { api } from "./client";
import type { SearchRequest, SearchResponse } from "@/types/search";

export const searchApi = {
  search: (data: SearchRequest) =>
    api.post<SearchResponse>("/search", data),
};
