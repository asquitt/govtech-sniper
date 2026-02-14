// -----------------------------------------------------------------------------
// Contract Types
// -----------------------------------------------------------------------------

import type { DataClassification } from "./proposal";

export type ContractStatus = "active" | "at_risk" | "completed" | "on_hold";

export type DeliverableStatus =
  | "pending"
  | "in_progress"
  | "submitted"
  | "approved"
  | "overdue";

export type ContractType = "prime" | "subcontract" | "idiq" | "task_order" | "bpa";
export type ModType = "administrative" | "funding" | "scope" | "period_of_performance" | "other";
export type CLINType = "ffp" | "t_and_m" | "cost_plus";

export interface ContractAward {
  id: number;
  user_id: number;
  rfp_id?: number | null;
  parent_contract_id?: number | null;
  contract_number: string;
  title: string;
  classification?: DataClassification;
  agency?: string | null;
  contract_type?: ContractType | null;
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

export interface ContractModification {
  id: number;
  contract_id: number;
  modification_number: string;
  mod_type?: ModType | null;
  description?: string | null;
  effective_date?: string | null;
  value_change?: number | null;
  created_at: string;
}

export interface ContractCLIN {
  id: number;
  contract_id: number;
  clin_number: string;
  description?: string | null;
  clin_type?: CLINType | null;
  unit_price?: number | null;
  quantity?: number | null;
  total_value?: number | null;
  funded_amount?: number | null;
  created_at: string;
  updated_at: string;
}
