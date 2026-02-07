export type SyncDirection = "push" | "pull" | "bidirectional";

export interface SharePointSyncConfig {
  id: number;
  user_id: number;
  proposal_id: number;
  sharepoint_folder: string;
  sync_direction: SyncDirection;
  auto_sync_enabled: boolean;
  watch_for_rfps: boolean;
  last_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SharePointSyncLog {
  id: number;
  config_id: number;
  action: string;
  status: string;
  details: Record<string, unknown>;
  created_at: string;
}
