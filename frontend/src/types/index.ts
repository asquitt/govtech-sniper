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
  source_type?: string;
  jurisdiction?: string;
  contract_vehicle?: string;
  incumbent_vendor?: string;
  buyer_contact_name?: string;
  buyer_contact_email?: string;
  buyer_contact_phone?: string;
  budget_estimate?: number;
  competitive_landscape?: string;
  intel_notes?: string;
  created_at: string;
  updated_at: string;
  analyzed_at?: string;
}

export interface RFPListItem {
  id: number;
  title: string;
  solicitation_number: string;
  notice_id?: string;
  agency: string;
  status: RFPStatus;
  is_qualified?: boolean;
  qualification_score?: number;
  recommendation_score?: number;
  response_deadline?: string;
  requirements_count?: number;
  sections_generated?: number;
  analyzed_at?: string;
  updated_at?: string;
  created_at: string;
}

// -----------------------------------------------------------------------------
// Saved Search Types
// -----------------------------------------------------------------------------

export interface SavedSearch {
  id: number;
  name: string;
  filters: Record<string, unknown>;
  is_active: boolean;
  last_run_at?: string | null;
  last_match_count: number;
  created_at: string;
  updated_at: string;
}

export interface SavedSearchRunResult {
  search_id: number;
  match_count: number;
  matches: RFPListItem[];
  ran_at: string;
}

// -----------------------------------------------------------------------------
// Award & Contact Intelligence
// -----------------------------------------------------------------------------

export interface AwardRecord {
  id: number;
  rfp_id?: number | null;
  notice_id?: string | null;
  solicitation_number?: string | null;
  contract_number?: string | null;
  agency?: string | null;
  awardee_name: string;
  award_amount?: number | null;
  award_date?: string | null;
  contract_vehicle?: string | null;
  naics_code?: string | null;
  set_aside?: string | null;
  place_of_performance?: string | null;
  description?: string | null;
  source_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface OpportunityContact {
  id: number;
  rfp_id?: number | null;
  name: string;
  role?: string | null;
  organization?: string | null;
  email?: string | null;
  phone?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

// -----------------------------------------------------------------------------
// Budget Intelligence
// -----------------------------------------------------------------------------

export interface BudgetIntelligence {
  id: number;
  rfp_id?: number | null;
  title: string;
  fiscal_year?: number | null;
  amount?: number | null;
  source_url?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

// -----------------------------------------------------------------------------
// Word Add-in Types
// -----------------------------------------------------------------------------

export type WordAddinSessionStatus = "active" | "paused" | "completed";

export interface WordAddinSession {
  id: number;
  proposal_id: number;
  document_name: string;
  status: WordAddinSessionStatus;
  metadata: Record<string, unknown>;
  last_synced_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WordAddinEvent {
  id: number;
  session_id: number;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

// -----------------------------------------------------------------------------
// Graphics Requests
// -----------------------------------------------------------------------------

export type GraphicsRequestStatus =
  | "requested"
  | "in_progress"
  | "delivered"
  | "rejected";

export interface ProposalGraphicRequest {
  id: number;
  proposal_id: number;
  section_id?: number | null;
  user_id: number;
  title: string;
  description?: string | null;
  status: GraphicsRequestStatus;
  due_date?: string | null;
  asset_url?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
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

export type CaptureFieldType = "text" | "number" | "select" | "date" | "boolean";

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

export interface CaptureCustomField {
  id: number;
  name: string;
  field_type: CaptureFieldType;
  options: string[];
  stage?: CaptureStage | null;
  is_required: boolean;
  created_at: string;
  updated_at: string;
}

export interface CaptureFieldValue {
  field: CaptureCustomField;
  value?: unknown | null;
}

export interface CaptureFieldValueList {
  fields: CaptureFieldValue[];
}

export interface CapturePlanListItem extends CapturePlan {
  rfp_title: string;
  rfp_agency?: string | null;
  rfp_status?: RFPStatus | null;
}

export interface CaptureCompetitor {
  id: number;
  rfp_id: number;
  user_id: number;
  name: string;
  incumbent: boolean;
  strengths?: string | null;
  weaknesses?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CaptureMatchInsight {
  plan_id: number;
  rfp_id: number;
  summary: string;
  factors: Array<{ factor: string; value: unknown }>;
}

export interface GateReview {
  id: number;
  rfp_id: number;
  reviewer_id: number;
  stage: CaptureStage;
  decision: BidDecision;
  notes?: string | null;
  created_at: string;
}

export interface TeamingPartner {
  id: number;
  name: string;
  partner_type?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TeamingPartnerLink {
  id: number;
  rfp_id: number;
  partner_id: number;
  role?: string | null;
  created_at: string;
}

// -----------------------------------------------------------------------------
// Contract Types
// -----------------------------------------------------------------------------

export type ContractStatus = "active" | "at_risk" | "completed" | "on_hold";

export type DeliverableStatus =
  | "pending"
  | "in_progress"
  | "submitted"
  | "approved"
  | "overdue";

export interface ContractAward {
  id: number;
  user_id: number;
  rfp_id?: number | null;
  contract_number: string;
  title: string;
  agency?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  value?: number | null;
  status: ContractStatus;
  summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContractDeliverable {
  id: number;
  contract_id: number;
  title: string;
  due_date?: string | null;
  status: DeliverableStatus;
  notes?: string | null;
  risk_flag?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContractTask {
  id: number;
  contract_id: number;
  title: string;
  due_date?: string | null;
  is_complete: boolean;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CPARSReview {
  id: number;
  contract_id: number;
  period_start?: string | null;
  period_end?: string | null;
  overall_rating?: string | null;
  notes?: string | null;
  created_at: string;
}

export interface CPARSEvidence {
  id: number;
  cpars_id: number;
  document_id: number;
  citation?: string | null;
  notes?: string | null;
  created_at: string;
  document_title?: string | null;
  document_type?: string | null;
}

export interface ContractStatusReport {
  id: number;
  contract_id: number;
  period_start?: string | null;
  period_end?: string | null;
  summary?: string | null;
  accomplishments?: string | null;
  risks?: string | null;
  next_steps?: string | null;
  created_at: string;
  updated_at: string;
}

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

// -----------------------------------------------------------------------------
// Integration Types
// -----------------------------------------------------------------------------

export type IntegrationProvider =
  | "okta"
  | "microsoft"
  | "sharepoint"
  | "salesforce"
  | "word_addin"
  | "webhook"
  | "slack";

export interface IntegrationConfig {
  id: number;
  provider: IntegrationProvider;
  name?: string | null;
  is_enabled: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface IntegrationFieldDefinition {
  key: string;
  label: string;
  secret: boolean;
  description?: string;
}

export interface IntegrationProviderDefinition {
  provider: IntegrationProvider;
  label: string;
  category: string;
  required_fields: IntegrationFieldDefinition[];
  optional_fields: IntegrationFieldDefinition[];
  supports_sync: boolean;
  supports_webhooks: boolean;
}

export interface IntegrationTestResult {
  status: "ok" | "error" | "disabled";
  message: string;
  missing_fields: string[];
  checked_at: string;
}

export interface IntegrationSyncRun {
  id: number;
  status: "pending" | "running" | "success" | "failed";
  items_synced: number;
  error?: string | null;
  details: Record<string, unknown>;
  started_at: string;
  completed_at?: string | null;
}

export interface IntegrationWebhookEvent {
  id: number;
  event_type: string;
  payload: Record<string, unknown>;
  received_at: string;
}

export interface IntegrationSsoAuthorizeResponse {
  provider: IntegrationProvider;
  authorization_url: string;
  state: string;
}

export interface AuditEvent {
  id: number;
  user_id?: number | null;
  entity_type: string;
  entity_id?: number | null;
  action: string;
  event_metadata: Record<string, unknown>;
  created_at: string;
}

export interface AuditSummary {
  period_days: number;
  total_events: number;
  by_action: Array<{ action: string; count: number }>;
  by_entity_type: Array<{ entity_type: string; count: number }>;
}

export interface ObservabilityMetrics {
  period_days: number;
  audit_events: { total: number };
  integration_syncs: {
    total: number;
    success: number;
    failed: number;
    last_sync_at?: string | null;
    by_provider: Record<string, { total: number; success: number; failed: number }>;
  };
  webhook_events: {
    total: number;
    by_provider: Record<string, number>;
  };
}

export interface CapturePlanListItem extends CapturePlan {
  rfp_title: string;
  rfp_agency?: string | null;
  rfp_status?: RFPStatus | null;
}

export interface CaptureCompetitor {
  id: number;
  rfp_id: number;
  user_id: number;
  name: string;
  incumbent: boolean;
  strengths?: string | null;
  weaknesses?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CaptureMatchInsight {
  plan_id: number;
  rfp_id: number;
  summary: string;
  factors: Array<{ factor: string; value: unknown }>;
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

export type RequirementStatus =
  | "open"
  | "in_progress"
  | "blocked"
  | "addressed";

export interface ComplianceRequirement {
  id: string;
  section: string;
  source_section?: string;
  requirement_text: string;
  importance: ImportanceLevel;
  category?: string;
  page_reference?: number;
  keywords: string[];
  is_addressed: boolean;
  notes?: string;
  status?: RequirementStatus;
  assigned_to?: string;
  tags?: string[];
  generated_content?: GeneratedContent;
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
  writing_plan?: string;
  status: SectionStatus;
  generated_content?: GeneratedContent;
  final_content?: string;
  word_count?: number;
  display_order: number;
  created_at: string;
  updated_at: string;
  generated_at?: string;
}

export interface SectionEvidence {
  id: number;
  section_id: number;
  document_id: number;
  chunk_id?: number | null;
  citation?: string | null;
  notes?: string | null;
  created_at: string;
  document_title?: string | null;
  document_filename?: string | null;
}

export type SubmissionPackageStatus =
  | "draft"
  | "in_review"
  | "ready"
  | "submitted";

export interface SubmissionPackage {
  id: number;
  proposal_id: number;
  owner_id?: number | null;
  title: string;
  status: SubmissionPackageStatus;
  due_date?: string | null;
  submitted_at?: string | null;
  checklist: Record<string, unknown>[];
  notes?: string | null;
  docx_export_path?: string | null;
  pdf_export_path?: string | null;
  created_at: string;
  updated_at: string;
}

export type OutlineStatus = "generating" | "draft" | "approved";

export interface OutlineSection {
  id: number;
  outline_id: number;
  parent_id?: number | null;
  title: string;
  description?: string | null;
  mapped_requirement_ids: string[];
  display_order: number;
  estimated_pages?: number | null;
  created_at: string;
  updated_at: string;
  children: OutlineSection[];
}

export interface ProposalOutline {
  id: number;
  proposal_id: number;
  status: OutlineStatus;
  created_at: string;
  updated_at: string;
  sections: OutlineSection[];
}

export interface ProposalFocusDocument {
  id: number;
  proposal_id: number;
  document_id: number;
  priority_order: number;
  created_at: string;
  document_title?: string;
  document_filename?: string;
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
