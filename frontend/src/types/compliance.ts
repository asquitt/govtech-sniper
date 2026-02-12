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
