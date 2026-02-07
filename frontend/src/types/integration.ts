// -----------------------------------------------------------------------------
// Integration Types
// -----------------------------------------------------------------------------

export type IntegrationProvider =
  | "okta"
  | "microsoft"
  | "sharepoint"
  | "salesforce"
  | "word_addin"
  | "webhook"
  | "slack";

export interface IntegrationConfig {
  id: number;
  provider: IntegrationProvider;
  name?: string | null;
  is_enabled: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface IntegrationFieldDefinition {
  key: string;
  label: string;
  secret: boolean;
  description?: string;
}

export interface IntegrationProviderDefinition {
  provider: IntegrationProvider;
  label: string;
  category: string;
  required_fields: IntegrationFieldDefinition[];
  optional_fields: IntegrationFieldDefinition[];
  supports_sync: boolean;
  supports_webhooks: boolean;
}

export interface IntegrationTestResult {
  status: "ok" | "error" | "disabled";
  message: string;
  missing_fields: string[];
  checked_at: string;
}

export interface IntegrationSyncRun {
  id: number;
  status: "pending" | "running" | "success" | "failed";
  items_synced: number;
  error?: string | null;
  details: Record<string, unknown>;
  started_at: string;
  completed_at?: string | null;
}

export interface IntegrationWebhookEvent {
  id: number;
  event_type: string;
  payload: Record<string, unknown>;
  received_at: string;
}

export interface IntegrationSsoAuthorizeResponse {
  provider: IntegrationProvider;
  authorization_url: string;
  state: string;
}

export interface AuditEvent {
  id: number;
  user_id?: number | null;
  entity_type: string;
  entity_id?: number | null;
  action: string;
  event_metadata: Record<string, unknown>;
  created_at: string;
}

export interface AuditSummary {
  period_days: number;
  total_events: number;
  by_action: Array<{ action: string; count: number }>;
  by_entity_type: Array<{ entity_type: string; count: number }>;
}

export interface ObservabilityMetrics {
  period_days: number;
  audit_events: { total: number };
  integration_syncs: {
    total: number;
    success: number;
    failed: number;
    last_sync_at?: string | null;
    by_provider: Record<string, { total: number; success: number; failed: number }>;
  };
  webhook_events: {
    total: number;
    by_provider: Record<string, number>;
  };
}
