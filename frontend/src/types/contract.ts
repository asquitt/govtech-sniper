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
