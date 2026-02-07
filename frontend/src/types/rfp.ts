// -----------------------------------------------------------------------------
// RFP Types
// -----------------------------------------------------------------------------

export type RFPStatus =
  | "new"
  | "analyzing"
  | "analyzed"
  | "drafting"
  | "ready"
  | "submitted"
  | "archived";

export type RFPType =
  | "solicitation"
  | "sources_sought"
  | "combined"
  | "presolicitation"
  | "award"
  | "special_notice";

export interface RFP {
  id: number;
  user_id: number;
  title: string;
  solicitation_number: string;
  agency: string;
  sub_agency?: string;
  naics_code?: string;
  set_aside?: string;
  rfp_type: RFPType;
  status: RFPStatus;
  posted_date?: string;
  response_deadline?: string;
  source_url?: string;
  sam_gov_link?: string;
  description?: string;
  summary?: string;
  is_qualified?: boolean;
  qualification_reason?: string;
  qualification_score?: number;
  estimated_value?: number;
  place_of_performance?: string;
  source_type?: string;
  jurisdiction?: string;
  contract_vehicle?: string;
  incumbent_vendor?: string;
  buyer_contact_name?: string;
  buyer_contact_email?: string;
  buyer_contact_phone?: string;
  budget_estimate?: number;
  competitive_landscape?: string;
  intel_notes?: string;
  created_at: string;
  updated_at: string;
  analyzed_at?: string;
}

export interface RFPListItem {
  id: number;
  title: string;
  solicitation_number: string;
  notice_id?: string;
  agency: string;
  status: RFPStatus;
  is_qualified?: boolean;
  qualification_score?: number;
  match_score?: number | null;
  recommendation_score?: number;
  response_deadline?: string;
  requirements_count?: number;
  sections_generated?: number;
  analyzed_at?: string;
  updated_at?: string;
  created_at: string;
}

// -----------------------------------------------------------------------------
// Saved Search Types
// -----------------------------------------------------------------------------

export interface SavedSearch {
  id: number;
  name: string;
  filters: Record<string, unknown>;
  is_active: boolean;
  last_run_at?: string | null;
  last_match_count: number;
  created_at: string;
  updated_at: string;
}

export interface SavedSearchRunResult {
  search_id: number;
  match_count: number;
  matches: RFPListItem[];
  ran_at: string;
}
