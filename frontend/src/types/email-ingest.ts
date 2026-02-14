export interface EmailIngestConfig {
  id: number;
  user_id: number;
  workspace_id: number | null;
  imap_server: string;
  imap_port: number;
  email_address: string;
  folder: string;
  is_enabled: boolean;
  auto_create_rfps: boolean;
  min_rfp_confidence: number;
  last_checked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmailIngestConfigCreate {
  imap_server: string;
  imap_port: number;
  email_address: string;
  password: string;
  folder?: string;
  workspace_id?: number | null;
  auto_create_rfps?: boolean;
  min_rfp_confidence?: number;
}

export interface EmailIngestConfigUpdate {
  imap_server?: string;
  imap_port?: number;
  email_address?: string;
  password?: string;
  folder?: string;
  is_enabled?: boolean;
  workspace_id?: number | null;
  auto_create_rfps?: boolean;
  min_rfp_confidence?: number;
}

export interface IngestedEmail {
  id: number;
  config_id: number;
  message_id: string;
  subject: string;
  sender: string;
  received_at: string;
  attachment_count: number;
  attachment_names: string[];
  processing_status: "pending" | "processed" | "ignored" | "error";
  classification_confidence: number | null;
  classification_reasons: string[];
  created_rfp_id: number | null;
  error_message: string | null;
  created_at: string;
  processed_at: string | null;
}

export interface EmailIngestSyncRequest {
  config_id?: number;
  run_poll?: boolean;
  run_process?: boolean;
  poll_limit?: number;
  process_limit?: number;
}

export interface EmailIngestSyncResponse {
  configs_checked: number;
  fetched: number;
  duplicates: number;
  poll_errors: number;
  processed: number;
  created_rfps: number;
  inbox_forwarded: number;
  process_errors: number;
}
