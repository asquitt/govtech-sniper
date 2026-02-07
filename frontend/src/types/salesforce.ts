// -----------------------------------------------------------------------------
// Salesforce Integration Types
// -----------------------------------------------------------------------------

export interface SalesforceFieldMapping {
  id: number;
  integration_id: number;
  sniper_field: string;
  salesforce_field: string;
  direction: "push" | "pull" | "both";
  transform?: string | null;
  created_at: string;
}

export interface SalesforceOpportunity {
  sf_id: string;
  name: string;
  amount?: number | null;
  stage?: string | null;
  close_date?: string | null;
}

export interface SalesforceSyncResult {
  status: "success" | "failed";
  pushed: number;
  pulled: number;
  errors: string[];
  completed_at: string;
}

export interface SalesforceStatus {
  configured: boolean;
  enabled: boolean;
  connected: boolean;
  error?: string;
}
