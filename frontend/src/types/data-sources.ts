// =============================================================================
// Data Sources — Type Definitions
// =============================================================================

export interface DataSourceProvider {
  provider_name: string;
  display_name: string;
  description: string;
  is_active: boolean;
  healthy?: boolean | null;
}

export interface DataSourceSearchParams {
  keywords?: string | null;
  naics_codes?: string[] | null;
  agency?: string | null;
  days_back?: number;
  limit?: number;
}

export interface RawOpportunity {
  external_id: string;
  title: string;
  agency?: string | null;
  description?: string | null;
  posted_date?: string | null;
  response_deadline?: string | null;
  estimated_value?: number | null;
  naics_code?: string | null;
  source_url?: string | null;
  source_type: string;
  raw_data?: Record<string, unknown> | null;
}

export interface DataSourceSearchResponse {
  provider: string;
  count: number;
  results: RawOpportunity[];
}

export interface DataSourceIngestResponse {
  provider: string;
  searched: number;
  created: number;
  skipped: number;
}

export interface DataSourceHealthResponse {
  provider: string;
  healthy: boolean;
}
