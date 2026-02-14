export interface CMMCDomainStatus {
  domain: string;
  domain_name: string;
  total_controls: number;
  met_controls: number;
  percentage: number;
}

export interface CMMCStatus {
  total_controls: number;
  met_controls: number;
  score_percentage: number;
  target_level: number;
  domains: CMMCDomainStatus[];
}

export interface NISTControlFamily {
  family_id: string;
  name: string;
  total_controls: number;
  implemented: number;
  partial: number;
  not_implemented: number;
}

export interface NISTOverview {
  framework: string;
  total_families: number;
  families: NISTControlFamily[];
  overall_coverage: number;
}

export interface DataPrivacyInfo {
  data_handling: string[];
  encryption: string[];
  access_controls: string[];
  data_retention: string[];
  certifications: string[];
}

export interface TrustCenterPolicy {
  allow_ai_requirement_analysis: boolean;
  allow_ai_draft_generation: boolean;
  require_human_review_for_submission: boolean;
  share_anonymized_product_telemetry: boolean;
  retain_prompt_logs_days: number;
  retain_output_logs_days: number;
}

export interface TrustCenterPolicyUpdate {
  allow_ai_requirement_analysis?: boolean;
  allow_ai_draft_generation?: boolean;
  require_human_review_for_submission?: boolean;
  share_anonymized_product_telemetry?: boolean;
  retain_prompt_logs_days?: number;
  retain_output_logs_days?: number;
}

export interface TrustCenterRuntimeGuarantees {
  model_provider: string;
  processing_mode: string;
  provider_training_allowed: boolean;
  provider_retention_hours: number;
  no_training_enforced: boolean;
}

export interface TrustCenterEvidenceItem {
  control: string;
  status: "enforced" | "warning" | "configured";
  detail: string;
}

export interface TrustCenterProfile {
  organization_id: number | null;
  organization_name: string | null;
  can_manage_policy: boolean;
  policy: TrustCenterPolicy;
  runtime_guarantees: TrustCenterRuntimeGuarantees;
  evidence: TrustCenterEvidenceItem[];
  updated_at: string;
}

export interface ComplianceAuditSummary {
  total_events: number;
  events_last_30_days: number;
  by_type: Record<string, number>;
  compliance_score: number;
}

export interface ComplianceReadinessProgram {
  id: string;
  name: string;
  status: string;
  percent_complete: number;
  next_milestone: string;
}

export interface ComplianceReadiness {
  programs: ComplianceReadinessProgram[];
  last_updated: string;
}
