export type ReviewType = "pink" | "red" | "gold";

export type ReviewStatus = "scheduled" | "in_progress" | "completed" | "cancelled";

export type AssignmentStatus = "pending" | "accepted" | "completed";

export type CommentSeverity = "critical" | "major" | "minor" | "suggestion";

export type CommentStatus = "open" | "accepted" | "rejected" | "resolved";

export interface ProposalReview {
  id: number;
  proposal_id: number;
  review_type: ReviewType;
  status: ReviewStatus;
  scheduled_date?: string | null;
  completed_date?: string | null;
  overall_score?: number | null;
  summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewAssignment {
  id: number;
  review_id: number;
  reviewer_user_id: number;
  status: AssignmentStatus;
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
  created_at: string;
}
