export type ReviewType = "pink" | "red" | "gold";

export type ReviewStatus = "scheduled" | "in_progress" | "completed" | "cancelled";

export type AssignmentStatus = "pending" | "accepted" | "completed";

export type CommentSeverity = "critical" | "major" | "minor" | "suggestion";

export type CommentStatus = "open" | "assigned" | "addressed" | "verified" | "closed" | "rejected";

export type ChecklistItemStatus = "pending" | "pass" | "fail" | "na";

export interface ProposalReview {
  id: number;
  proposal_id: number;
  review_type: ReviewType;
  status: ReviewStatus;
  scheduled_date?: string | null;
  completed_date?: string | null;
  overall_score?: number | null;
  summary?: string | null;
  go_no_go_decision?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewAssignment {
  id: number;
  review_id: number;
  reviewer_user_id: number;
  status: AssignmentStatus;
  due_date?: string | null;
  completed_at?: string | null;
  assigned_at: string;
}

export interface ReviewComment {
  id: number;
  review_id: number;
  section_id?: number | null;
  reviewer_user_id: number;
  comment_text: string;
  severity: CommentSeverity;
  status: CommentStatus;
  resolution_note?: string | null;
  assigned_to_user_id?: number | null;
  resolved_by_user_id?: number | null;
  verified_by_user_id?: number | null;
  resolved_at?: string | null;
  verified_at?: string | null;
  anchor_text?: string | null;
  anchor_offset_start?: number | null;
  anchor_offset_end?: number | null;
  is_inline?: boolean;
  mentions?: number[] | null;
  created_at: string;
}

export interface ReviewChecklistItem {
  id: number;
  review_id: number;
  category: string;
  item_text: string;
  status: ChecklistItemStatus;
  reviewer_note?: string | null;
  display_order: number;
  created_at: string;
}

export interface ScoringSummary {
  review_id: number;
  review_type: ReviewType;
  average_score?: number | null;
  min_score?: number | null;
  max_score?: number | null;
  checklist_pass_rate: number;
  comments_by_severity: Record<string, number>;
  resolution_rate: number;
  total_comments: number;
  resolved_comments: number;
}

export interface ReviewDashboardItem {
  review_id: number;
  proposal_id: number;
  proposal_title: string;
  review_type: ReviewType;
  status: ReviewStatus;
  scheduled_date?: string | null;
  overall_score?: number | null;
  go_no_go_decision?: string | null;
  total_comments: number;
  open_comments: number;
  total_assignments: number;
  completed_assignments: number;
}

export interface ReviewPacketActionItem {
  rank: number;
  comment_id: number;
  section_id?: number | null;
  severity: CommentSeverity;
  status: CommentStatus;
  risk_score: number;
  age_days: number;
  assigned_to_user_id?: number | null;
  recommended_action: string;
  rationale: string;
}

export interface ReviewPacketChecklistSummary {
  total_items: number;
  pass_count: number;
  fail_count: number;
  pending_count: number;
  na_count: number;
  pass_rate: number;
}

export interface ReviewPacketRiskSummary {
  open_critical: number;
  open_major: number;
  unresolved_comments: number;
  highest_risk_score: number;
  overall_risk_level: "high" | "medium" | "low";
}

export interface ReviewPacket {
  review_id: number;
  proposal_id: number;
  proposal_title: string;
  review_type: ReviewType;
  review_status: ReviewStatus;
  generated_at: string;
  checklist_summary: ReviewPacketChecklistSummary;
  risk_summary: ReviewPacketRiskSummary;
  action_queue: ReviewPacketActionItem[];
  recommended_exit_criteria: string[];
}
