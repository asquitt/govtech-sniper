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
  created_at: string;
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
  locked_at: string;
}

export interface DocumentPresence {
  proposal_id: number;
  users: DocumentPresenceUser[];
  locks: SectionLock[];
}
