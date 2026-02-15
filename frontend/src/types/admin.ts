// =============================================================================
// Admin & Organization Types
// =============================================================================

export type OrgRole = "owner" | "admin" | "member" | "viewer";
export type SSOProviderType = "okta" | "microsoft" | "google";

export interface OrganizationDetails {
  id: number;
  name: string;
  slug: string;
  domain: string | null;
  billing_email: string | null;
  sso_enabled: boolean;
  sso_provider: SSOProviderType | null;
  sso_enforce: boolean;
  sso_auto_provision: boolean;
  logo_url: string | null;
  primary_color: string | null;
  ip_allowlist: string[];
  data_retention_days: number;
  require_step_up_for_sensitive_exports: boolean;
  require_step_up_for_sensitive_shares: boolean;
  apply_cui_watermark_to_sensitive_exports: boolean;
  apply_cui_redaction_to_sensitive_exports: boolean;
  member_count: number;
  created_at: string;
}

export interface OrgMember {
  id: number;
  user_id: number;
  email: string;
  full_name: string | null;
  role: OrgRole;
  is_active: boolean;
  tier: string;
  joined_at: string;
  last_login: string | null;
  sso_provider: SSOProviderType | null;
}

export type OrgInvitationStatus = "pending" | "activated" | "expired" | "revoked";

export interface OrgMemberInvitation {
  id: number;
  email: string;
  role: OrgRole;
  status: OrgInvitationStatus;
  expires_at: string;
  activated_at: string | null;
  accepted_user_id: number | null;
  invited_by_user_id: number;
  activation_ready: boolean;
  invite_age_hours: number;
  invite_age_days: number;
  days_until_expiry: number;
  sla_state: "healthy" | "expiring" | "aging" | "expired" | "completed" | "revoked";
}

export interface OrgUsageAnalytics {
  members: number;
  proposals: number;
  rfps: number;
  audit_events: number;
  active_users: number;
  by_action: { action: string; count: number }[];
  period_days: number;
}

export interface OrgAuditEvent {
  id: number;
  user_id: number | null;
  user_email: string | null;
  entity_type: string;
  entity_id: string | null;
  action: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AdminCapabilityHealthRuntime {
  debug: boolean;
  mock_ai: boolean;
  mock_sam_gov: boolean;
  database_engine: string;
  websocket: {
    endpoint: string;
    active_connections: number;
    watched_tasks: number;
    active_documents: number;
    presence_users: number;
    active_section_locks: number;
    active_cursors: number;
  };
}

export interface AdminCapabilityHealthWorkers {
  broker_reachable: boolean;
  worker_online: boolean;
  task_mode: "queued" | "sync_fallback";
}

export interface AdminCapabilityHealthEnterprise {
  scim_configured: boolean;
  scim_default_team_name: string;
  webhook_subscriptions: number;
  stored_secrets: number;
}

export interface AdminCapabilityHealthIntegrationProvider {
  provider: string;
  total: number;
  enabled: number;
}

export interface AdminCapabilityHealthDiscoverabilityItem {
  capability: string;
  frontend_path: string | null;
  backend_prefix: string;
  status: "integrated" | "ready" | "configured" | "needs_configuration";
  note: string;
}

export interface AdminCapabilityHealth {
  organization_id: number;
  timestamp: string;
  runtime: AdminCapabilityHealthRuntime;
  workers: AdminCapabilityHealthWorkers;
  enterprise: AdminCapabilityHealthEnterprise;
  integrations_by_provider: AdminCapabilityHealthIntegrationProvider[];
  discoverability: AdminCapabilityHealthDiscoverabilityItem[];
}
