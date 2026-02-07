export interface EmailIngestConfig {
  id: number;
  user_id: number;
  imap_server: string;
  imap_port: number;
  email_address: string;
  folder: string;
  is_enabled: boolean;
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
}

export interface EmailIngestConfigUpdate {
  imap_server?: string;
  imap_port?: number;
  email_address?: string;
  password?: string;
  folder?: string;
  is_enabled?: boolean;
}

export interface IngestedEmail {
  id: number;
  config_id: number;
  message_id: string;
  subject: string;
  sender: string;
  received_at: string;
  processing_status: "pending" | "processed" | "ignored" | "error";
  created_rfp_id: number | null;
  error_message: string | null;
  created_at: string;
}
