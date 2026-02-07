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
