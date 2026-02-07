export interface SearchRequest {
  query: string;
  entity_types?: string[];
  limit?: number;
}

export interface SearchResult {
  entity_type: string;
  entity_id: number;
  chunk_text: string;
  score: number;
  chunk_index: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}
