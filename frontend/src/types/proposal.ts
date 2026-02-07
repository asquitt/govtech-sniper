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
