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
