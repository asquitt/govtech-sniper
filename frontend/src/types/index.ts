// =============================================================================
// RFP Sniper - TypeScript Type Definitions
// =============================================================================

// -----------------------------------------------------------------------------
// RFP Types
// -----------------------------------------------------------------------------

export type RFPStatus =
  | "new"
  | "analyzing"
  | "analyzed"
  | "drafting"
  | "ready"
  | "submitted"
  | "archived";

export type RFPType =
  | "solicitation"
  | "sources_sought"
  | "combined"
  | "presolicitation"
  | "award"
  | "special_notice";

export interface RFP {
  id: number;
  user_id: number;
  title: string;
  solicitation_number: string;
  agency: string;
  sub_agency?: string;
  naics_code?: string;
  set_aside?: string;
  rfp_type: RFPType;
  status: RFPStatus;
  posted_date?: string;
  response_deadline?: string;
  source_url?: string;
  sam_gov_link?: string;
  description?: string;
  summary?: string;
  is_qualified?: boolean;
  qualification_reason?: string;
  qualification_score?: number;
  estimated_value?: number;
  place_of_performance?: string;
  created_at: string;
  updated_at: string;
  analyzed_at?: string;
}

export interface RFPListItem {
  id: number;
  title: string;
  solicitation_number: string;
  agency: string;
  status: RFPStatus;
  is_qualified?: boolean;
  qualification_score?: number;
  recommendation_score?: number;
  response_deadline?: string;
  created_at: string;
}

// -----------------------------------------------------------------------------
// Capture Types
// -----------------------------------------------------------------------------

export type CaptureStage =
  | "identified"
  | "qualified"
  | "pursuit"
  | "proposal"
  | "submitted"
  | "won"
  | "lost";

export type BidDecision = "pending" | "bid" | "no_bid";

export interface CapturePlan {
  id: number;
  rfp_id: number;
  owner_id: number;
  stage: CaptureStage;
  bid_decision: BidDecision;
  win_probability?: number | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CapturePlanListItem extends CapturePlan {
  rfp_title: string;
  rfp_agency?: string | null;
  rfp_status?: RFPStatus | null;
}

// -----------------------------------------------------------------------------
// Capture Types
// -----------------------------------------------------------------------------

export type CaptureStage =
  | "identified"
  | "qualified"
  | "pursuit"
  | "proposal"
  | "submitted"
  | "won"
  | "lost";

export type BidDecision = "pending" | "bid" | "no_bid";

export interface CapturePlan {
  id: number;
  rfp_id: number;
  owner_id: number;
  stage: CaptureStage;
  bid_decision: BidDecision;
  win_probability?: number | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CapturePlanListItem extends CapturePlan {
  rfp_title: string;
  rfp_agency?: string | null;
  rfp_status?: RFPStatus | null;
}

// -----------------------------------------------------------------------------
// Compliance Matrix Types
// -----------------------------------------------------------------------------

export type ImportanceLevel =
  | "mandatory"
  | "evaluated"
  | "optional"
  | "informational";

export type RequirementType =
  | "Technical"
  | "Management"
  | "Past Performance"
  | "Pricing"
  | "Administrative"
  | "Personnel"
  | "Quality"
  | "Security";

export interface ComplianceRequirement {
  id: string;
  section: string;
  requirement_text: string;
  importance: ImportanceLevel;
  category?: string;
  page_reference?: number;
  keywords: string[];
  is_addressed: boolean;
  notes?: string;
}

export interface ComplianceMatrix {
  id: number;
  rfp_id: number;
  requirements: ComplianceRequirement[];
  total_requirements: number;
  mandatory_count: number;
  addressed_count: number;
  extraction_confidence?: number;
  created_at: string;
  updated_at: string;
}

// -----------------------------------------------------------------------------
// Proposal Types
// -----------------------------------------------------------------------------

export type ProposalStatus =
  | "draft"
  | "in_progress"
  | "review"
  | "final"
  | "submitted";

export type SectionStatus =
  | "pending"
  | "generating"
  | "generated"
  | "editing"
  | "approved";

export interface Citation {
  source_file: string;
  page_number?: number;
  section?: string;
  quote?: string;
  confidence: number;
}

export interface GeneratedContent {
  raw_text: string;
  clean_text: string;
  citations: Citation[];
  model_used: string;
  tokens_used: number;
  generation_time_seconds: number;
}

export interface ProposalSection {
  id: number;
  proposal_id: number;
  title: string;
  section_number: string;
  requirement_id?: string;
  requirement_text?: string;
  status: SectionStatus;
  generated_content?: GeneratedContent;
  final_content?: string;
  word_count?: number;
  display_order: number;
  created_at: string;
  updated_at: string;
  generated_at?: string;
}

export interface Proposal {
  id: number;
  user_id: number;
  rfp_id: number;
  title: string;
  version: number;
  status: ProposalStatus;
  executive_summary?: string;
  total_sections: number;
  completed_sections: number;
  compliance_score?: number;
  created_at: string;
  updated_at: string;
  submitted_at?: string;
  completion_percentage: number;
}

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

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface TaskResponse {
  task_id: string;
  message: string;
  status: string;
}

export interface TaskStatus {
  task_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  result?: unknown;
  error?: string;
}

export interface SAMSearchParams {
  keywords: string;
  days_back?: number;
  limit?: number;
  naics_codes?: string[];
  set_aside_types?: string[];
  active_only?: boolean;
}

export interface DraftRequest {
  requirement_id: string;
  additional_context?: string;
  max_words?: number;
  tone?: "professional" | "technical" | "executive";
  include_citations?: boolean;
}

// -----------------------------------------------------------------------------
// UI State Types
// -----------------------------------------------------------------------------

export interface SidebarNavItem {
  title: string;
  href: string;
  icon: string;
  badge?: string | number;
}

export interface TableColumn<T> {
  key: keyof T;
  header: string;
  width?: string;
  render?: (value: T[keyof T], item: T) => React.ReactNode;
}
