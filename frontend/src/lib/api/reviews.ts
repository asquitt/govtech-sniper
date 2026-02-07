import api from "./client";
import type {
  ProposalReview,
  ReviewAssignment,
  ReviewComment,
  ReviewChecklistItem,
  ReviewDashboardItem,
  ScoringSummary,
  ReviewType,
  CommentSeverity,
  CommentStatus,
  ChecklistItemStatus,
} from "@/types";

export const reviewApi = {
  // Reviews
  scheduleReview: async (
    proposalId: number,
    payload: { review_type: ReviewType; scheduled_date?: string | null }
  ): Promise<ProposalReview> => {
    const { data } = await api.post(
      `/reviews/proposals/${proposalId}/reviews`,
      payload
    );
    return data;
  },

  listReviews: async (proposalId: number): Promise<ProposalReview[]> => {
    const { data } = await api.get(
      `/reviews/proposals/${proposalId}/reviews`
    );
    return data;
  },

  // Dashboard
  getDashboard: async (): Promise<ReviewDashboardItem[]> => {
    const { data } = await api.get("/reviews/dashboard");
    return data;
  },

  // Assignments
  assignReviewer: async (
    reviewId: number,
    payload: { reviewer_user_id: number; due_date?: string | null }
  ): Promise<ReviewAssignment> => {
    const { data } = await api.post(
      `/reviews/${reviewId}/assign`,
      payload
    );
    return data;
  },

  // Comments
  addComment: async (
    reviewId: number,
    payload: {
      section_id?: number | null;
      comment_text: string;
      severity?: CommentSeverity;
    }
  ): Promise<ReviewComment> => {
    const { data } = await api.post(
      `/reviews/${reviewId}/comments`,
      payload
    );
    return data;
  },

  listComments: async (reviewId: number): Promise<ReviewComment[]> => {
    const { data } = await api.get(`/reviews/${reviewId}/comments`);
    return data;
  },

  updateComment: async (
    reviewId: number,
    commentId: number,
    payload: {
      status?: CommentStatus;
      resolution_note?: string;
      assigned_to_user_id?: number | null;
    }
  ): Promise<ReviewComment> => {
    const { data } = await api.patch(
      `/reviews/${reviewId}/comments/${commentId}`,
      payload
    );
    return data;
  },

  // Checklists
  createChecklist: async (
    reviewId: number,
    payload: { review_type: string }
  ): Promise<ReviewChecklistItem[]> => {
    const { data } = await api.post(
      `/reviews/${reviewId}/checklist`,
      payload
    );
    return data;
  },

  getChecklist: async (reviewId: number): Promise<ReviewChecklistItem[]> => {
    const { data } = await api.get(`/reviews/${reviewId}/checklist`);
    return data;
  },

  updateChecklistItem: async (
    reviewId: number,
    itemId: number,
    payload: { status?: ChecklistItemStatus; reviewer_note?: string }
  ): Promise<ReviewChecklistItem> => {
    const { data } = await api.patch(
      `/reviews/${reviewId}/checklist/${itemId}`,
      payload
    );
    return data;
  },

  // Scoring summary
  getScoringSummary: async (reviewId: number): Promise<ScoringSummary> => {
    const { data } = await api.get(`/reviews/${reviewId}/scoring-summary`);
    return data;
  },

  // Complete
  completeReview: async (
    reviewId: number,
    payload: {
      overall_score: number;
      summary?: string;
      go_no_go_decision?: string;
    }
  ): Promise<ProposalReview> => {
    const { data } = await api.patch(
      `/reviews/${reviewId}/complete`,
      payload
    );
    return data;
  },
};
