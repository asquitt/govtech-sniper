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

export interface ComplianceReadinessCheckpoint {
  checkpoint_id: string;
  program_id: string;
  title: string;
  status: string;
  target_date: string;
  owner: string;
  third_party_required: boolean;
  evidence_items_ready: number;
  evidence_items_total: number;
  evidence_source?: "static" | "registry" | null;
  evidence_last_updated_at?: string | null;
  assessor_signoff_status?: "pending" | "approved" | "rejected" | null;
  assessor_signoff_by?: string | null;
  assessor_signed_at?: string | null;
}

export interface ComplianceReadinessCheckpointSnapshot {
  checkpoints: ComplianceReadinessCheckpoint[];
  generated_at: string;
}

export interface ComplianceTrustMetrics {
  generated_at: string;
  window_days: number;
  checkpoint_evidence_completeness_rate: number | null;
  checkpoint_signoff_completion_rate: number | null;
  trust_export_success_rate_30d: number | null;
  trust_export_successes_30d: number;
  trust_export_failures_30d: number;
  step_up_challenge_success_rate_30d: number | null;
  step_up_challenge_successes_30d: number;
  step_up_challenge_failures_30d: number;
  trust_ci_pass_rate_30d: number | null;
}

export interface ComplianceRegistryEvidenceItem {
  id: number;
  user_id: number;
  title: string;
  evidence_type: string;
  description: string | null;
  file_path: string | null;
  url: string | null;
  collected_at: string;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ComplianceCheckpointEvidenceItem {
  link_id: number;
  checkpoint_id: string;
  evidence_id: number;
  title: string;
  evidence_type: string;
  description: string | null;
  file_path: string | null;
  url: string | null;
  collected_at: string;
  expires_at: string | null;
  status: "submitted" | "accepted" | "rejected";
  notes: string | null;
  reviewer_user_id: number | null;
  reviewer_notes: string | null;
  reviewed_at: string | null;
  linked_at: string;
}

export interface ComplianceCheckpointEvidenceCreate {
  evidence_id: number;
  status?: "submitted" | "accepted" | "rejected";
  notes?: string;
}

export interface ComplianceCheckpointEvidenceUpdate {
  status?: "submitted" | "accepted" | "rejected";
  reviewer_notes?: string;
}

export interface ComplianceCheckpointSignoff {
  checkpoint_id: string;
  status: "pending" | "approved" | "rejected";
  assessor_name: string;
  assessor_org: string | null;
  notes: string | null;
  signed_by_user_id: number | null;
  signed_at: string | null;
  updated_at: string;
}

export interface ComplianceCheckpointSignoffWrite {
  status: "pending" | "approved" | "rejected";
  assessor_name: string;
  assessor_org?: string;
  notes?: string;
}

export interface GovCloudMigrationPhase {
  phase_id: string;
  title: string;
  status: string;
  target_date: string;
  owner: string;
  exit_criteria: string[];
}

export interface GovCloudDeploymentProfile {
  program_id: string;
  provider: string;
  status: string;
  target_regions: string[];
  boundary_services: string[];
  identity_federation_status: string;
  network_isolation_status: string;
  data_residency_status: string;
  migration_phases: GovCloudMigrationPhase[];
  updated_at: string;
}

export interface SOC2ControlDomainStatus {
  domain_id: string;
  domain_name: string;
  controls_total: number;
  controls_ready: number;
  percent_complete: number;
  owner: string;
}

export interface SOC2Milestone {
  milestone_id: string;
  title: string;
  status: string;
  due_date: string;
  owner: string;
  evidence_ready: boolean;
  notes: string;
}

export interface SOC2Readiness {
  program_id: string;
  name: string;
  status: string;
  audit_firm_status: string;
  observation_window_start: string;
  observation_window_end: string;
  overall_percent_complete: number;
  domains: SOC2ControlDomainStatus[];
  milestones: SOC2Milestone[];
  updated_at: string;
}
