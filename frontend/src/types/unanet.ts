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
}
