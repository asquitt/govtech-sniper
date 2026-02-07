// -----------------------------------------------------------------------------
// Knowledge Base Types
// -----------------------------------------------------------------------------

export type DocumentType =
  | "resume"
  | "past_performance"
  | "capability_statement"
  | "technical_spec"
  | "case_study"
  | "certification"
  | "contract"
  | "other";

export type ProcessingStatus = "pending" | "processing" | "ready" | "error";

export interface KnowledgeBaseDocument {
  id: number;
  user_id: number;
  title: string;
  document_type: DocumentType;
  description?: string;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  page_count?: number;
  processing_status: ProcessingStatus;
  processing_error?: string;
  gemini_cache_name?: string;
  gemini_cache_expires_at?: string;
  tags: string[];
  times_cited: number;
  last_cited_at?: string;
  created_at: string;
  updated_at: string;
  processed_at?: string;
  is_ready: boolean;
}
