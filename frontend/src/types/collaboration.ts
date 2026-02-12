export type WorkspaceRole = "viewer" | "contributor" | "admin";

export type SharedDataType =
  | "rfp_summary"
  | "compliance_matrix"
  | "proposal_section"
  | "forecast"
  | "contract_feed";

export interface SharedWorkspace {
  id: number;
  owner_id: number;
  rfp_id?: number | null;
  name: string;
  description?: string | null;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceInvitation {
  id: number;
  workspace_id: number;
  email: string;
  role: WorkspaceRole;
  accept_token?: string | null;
  is_accepted: boolean;
  expires_at: string;
  created_at: string;
}

export interface WorkspaceMember {
  id: number;
  workspace_id: number;
  user_id: number;
  role: WorkspaceRole;
  user_email?: string | null;
  user_name?: string | null;
  created_at: string;
}

export interface SharedDataPermission {
  id: number;
  workspace_id: number;
  data_type: SharedDataType;
  entity_id: number;
  label?: string | null;
  requires_approval: boolean;
  approval_status: "pending" | "approved" | "revoked";
  approved_by_user_id?: number | null;
  approved_at?: string | null;
  expires_at?: string | null;
  partner_user_id?: number | null;
  created_at: string;
}

export interface ContractFeedCatalogItem {
  id: number;
  name: string;
  source: string;
  description: string;
}

export interface ContractFeedPresetItem {
  key: string;
  name: string;
  description: string;
  feed_ids: number[];
}

export interface SharePresetApplyResponse {
  preset_key: string;
  applied_count: number;
  shared_items: SharedDataPermission[];
}

export interface ShareGovernanceSummary {
  workspace_id: number;
  total_shared_items: number;
  pending_approval_count: number;
  approved_count: number;
  revoked_count: number;
  expired_count: number;
  expiring_7d_count: number;
  scoped_share_count: number;
  global_share_count: number;
}

export interface ShareGovernanceTrendPoint {
  date: string;
  shared_count: number;
  approvals_completed_count: number;
  approved_within_sla_count: number;
  approved_after_sla_count: number;
  average_approval_hours?: number | null;
}

export interface ShareGovernanceTrends {
  workspace_id: number;
  days: number;
  sla_hours: number;
  overdue_pending_count: number;
  sla_approval_rate: number;
  points: ShareGovernanceTrendPoint[];
}

export interface GovernanceAnomaly {
  code: string;
  severity: "info" | "warning" | "critical";
  title: string;
  description: string;
  metric_value: number;
  threshold: number;
  recommendation: string;
}

export interface ComplianceDigestSchedule {
  workspace_id: number;
  user_id: number;
  frequency: "daily" | "weekly";
  day_of_week: number | null;
  hour_utc: number;
  minute_utc: number;
  channel: "in_app" | "email";
  anomalies_only: boolean;
  is_enabled: boolean;
  last_sent_at: string | null;
}

export interface ComplianceDigestPreview {
  workspace_id: number;
  generated_at: string;
  summary: ShareGovernanceSummary;
  trends: ShareGovernanceTrends;
  anomalies: GovernanceAnomaly[];
  schedule: ComplianceDigestSchedule;
}

export interface PortalView {
  workspace_name: string;
  workspace_description?: string | null;
  rfp_title?: string | null;
  shared_items: SharedDataPermission[];
  members: WorkspaceMember[];
}

// Real-Time Presence & Section Locking

export interface DocumentPresenceUser {
  user_id: number;
  user_name: string;
  joined_at: string;
}

export interface SectionLock {
  section_id: number;
  user_id: number;
  user_name: string;
  proposal_id?: number | null;
  locked_at: string;
}

export interface DocumentPresence {
  proposal_id: number;
  users: DocumentPresenceUser[];
  locks: SectionLock[];
}

// Inbox

export type InboxMessageType = "general" | "opportunity_alert" | "rfp_forward";

export interface InboxMessage {
  id: number;
  workspace_id: number;
  sender_id: number;
  sender_name?: string | null;
  sender_email?: string | null;
  subject: string;
  body: string;
  message_type: InboxMessageType;
  is_read: boolean;
  read_by: number[];
  attachments: string[];
  created_at: string;
  updated_at: string;
}

export interface InboxListResponse {
  items: InboxMessage[];
  total: number;
  page: number;
  page_size: number;
}

// Cursor Presence

export interface CursorPosition {
  user_id: number;
  user_name: string;
  section_id: number | null;
  position: number | null;
  color?: string;
  timestamp?: string;
  updated_at?: string;
}
