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
