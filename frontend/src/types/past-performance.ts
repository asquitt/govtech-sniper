export interface PastPerformanceMetadata {
  contract_number?: string;
  performing_agency?: string;
  contract_value?: number;
  period_of_performance_start?: string;
  period_of_performance_end?: string;
  naics_code?: string;
  relevance_tags?: string[];
}

export interface PastPerformanceDocument {
  id: number;
  title: string;
  document_type: string;
  contract_number?: string;
  performing_agency?: string;
  contract_value?: number;
  period_of_performance_start?: string;
  period_of_performance_end?: string;
  naics_code?: string;
  relevance_tags: string[];
  created_at: string;
}

export interface PastPerformanceListResponse {
  documents: PastPerformanceDocument[];
  total: number;
}

export interface MatchResult {
  document_id: number;
  title: string;
  score: number;
  matching_criteria: string[];
}

export interface MatchResponse {
  rfp_id: number;
  matches: MatchResult[];
  total: number;
}

export interface NarrativeResponse {
  document_id: number;
  rfp_id: number;
  narrative: string;
}
