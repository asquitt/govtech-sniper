// -----------------------------------------------------------------------------
// Dash Types
// -----------------------------------------------------------------------------

export type DashRole = "user" | "assistant" | "system";

export interface DashSession {
  id: number;
  title?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DashMessage {
  id: number;
  session_id: number;
  role: DashRole;
  content: string;
  citations: Record<string, unknown>[];
  created_at: string;
}
