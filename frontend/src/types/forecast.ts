export type ForecastSource = "sam_gov" | "agency_plan" | "budget_doc" | "manual";

export interface ProcurementForecast {
  id: number;
  user_id: number;
  title: string;
  agency?: string | null;
  naics_code?: string | null;
  estimated_value?: number | null;
  expected_solicitation_date?: string | null;
  expected_award_date?: string | null;
  fiscal_year?: number | null;
  source: ForecastSource;
  source_url?: string | null;
  description?: string | null;
  linked_rfp_id?: number | null;
  match_score?: number | null;
  created_at: string;
  updated_at: string;
}

export interface ForecastAlert {
  id: number;
  user_id: number;
  forecast_id: number;
  rfp_id: number;
  match_score: number;
  match_reason?: string | null;
  is_dismissed: boolean;
  created_at: string;
  forecast_title?: string | null;
  rfp_title?: string | null;
}
