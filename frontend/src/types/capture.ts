import type { RFPStatus } from "./rfp";

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
  company_duns?: string | null;
  cage_code?: string | null;
  naics_codes?: string[];
  set_asides?: string[];
  capabilities?: string[];
  clearance_level?: string | null;
  past_performance_summary?: string | null;
  website?: string | null;
  is_public?: boolean;
  created_at: string;
  updated_at: string;
}

export interface TeamingPartnerPublicProfile {
  id: number;
  name: string;
  partner_type?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  company_duns?: string | null;
  cage_code?: string | null;
  naics_codes: string[];
  set_asides: string[];
  capabilities: string[];
  clearance_level?: string | null;
  past_performance_summary?: string | null;
  website?: string | null;
}

export type TeamingRequestStatus = "pending" | "accepted" | "declined";

export interface TeamingRequest {
  id: number;
  from_user_id: number;
  to_partner_id: number;
  rfp_id?: number | null;
  message?: string | null;
  status: TeamingRequestStatus;
  partner_name?: string | null;
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

export type ActivityStatus = "planned" | "in_progress" | "completed" | "overdue";

export interface CaptureActivity {
  id: number;
  capture_plan_id: number;
  title: string;
  start_date?: string | null;
  end_date?: string | null;
  is_milestone: boolean;
  status: ActivityStatus;
  sort_order: number;
  depends_on_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface GanttPlanRow {
  plan_id: number;
  rfp_id: number;
  rfp_title: string;
  agency?: string | null;
  stage: CaptureStage;
  response_deadline?: string | null;
  activities: CaptureActivity[];
}

// -----------------------------------------------------------------------------
// Bid Scorecard Types
// -----------------------------------------------------------------------------

export type BidScorecardRecommendation = "bid" | "no_bid" | "conditional";
export type ScorerType = "ai" | "human";

export interface CriteriaScore {
  name: string;
  weight: number;
  score: number;
  reasoning?: string;
}

export interface BidScorecard {
  id: number;
  rfp_id: number;
  user_id: number;
  criteria_scores: CriteriaScore[];
  overall_score: number | null;
  recommendation: BidScorecardRecommendation | null;
  confidence: number | null;
  reasoning: string | null;
  scorer_type: ScorerType;
  scorer_id: number | null;
  created_at: string;
}

export interface BidDecisionSummary {
  rfp_id: number;
  total_votes: number;
  ai_score: number | null;
  human_avg: number | null;
  overall_recommendation: string | null;
  bid_count: number;
  no_bid_count: number;
  conditional_count: number;
}

// ---------------------------------------------------------------------------
// Capability Gap Analysis
// ---------------------------------------------------------------------------

export interface CapabilityGapItem {
  gap_type: string;
  description: string;
  required_value?: string | null;
  matching_partner_ids: number[];
}

export interface RecommendedPartner {
  partner_id: number;
  name: string;
  reason: string;
}

export interface CapabilityGapResult {
  rfp_id: number;
  gaps: CapabilityGapItem[];
  recommended_partners: RecommendedPartner[];
  analysis_summary: string;
}
