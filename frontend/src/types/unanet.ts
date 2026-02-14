// -----------------------------------------------------------------------------
// Unanet Integration Types
// -----------------------------------------------------------------------------

export interface UnanetProject {
  id: string;
  name: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  budget: number;
  percent_complete: number;
}

export interface UnanetSyncResult {
  status: "success" | "failed";
  projects_synced: number;
  errors: string[];
  synced_at: string;
}

export interface UnanetStatus {
  configured: boolean;
  enabled: boolean;
  base_url?: string;
  healthy?: boolean | null;
  resources_supported?: boolean;
  financials_supported?: boolean;
}

export interface UnanetResource {
  id: string;
  labor_category: string;
  role: string;
  hourly_rate: number;
  cost_rate: number;
  currency: string;
  availability_hours: number;
  source_project_id: string | null;
  effective_date: string | null;
  is_active: boolean;
}

export interface UnanetFinancialRecord {
  id: string;
  project_id: string | null;
  project_name: string;
  fiscal_year: number | null;
  booked_revenue: number;
  funded_value: number;
  invoiced_to_date: number;
  remaining_value: number;
  burn_rate_percent: number;
  currency: string;
  status: string;
  as_of_date: string | null;
}

export interface UnanetResourceSyncResult {
  status: "success" | "failed";
  resources_synced: number;
  errors: string[];
  synced_at: string;
}

export interface UnanetFinancialSyncResult {
  status: "success" | "failed";
  records_synced: number;
  total_funded_value: number;
  errors: string[];
  synced_at: string;
}
