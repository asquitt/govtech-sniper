import api from "./client";
import type {
  ProposalReview,
  ReviewAssignment,
  ReviewComment,
  ReviewType,
  CommentSeverity,
  CommentStatus,
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

  // Assignments
  assignReviewer: async (
    reviewId: number,
    payload: { reviewer_user_id: number }
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
    payload: { status?: CommentStatus; resolution_note?: string }
  ): Promise<ReviewComment> => {
    const { data } = await api.patch(
      `/reviews/${reviewId}/comments/${commentId}`,
      payload
    );
    return data;
  },

  // Complete
  completeReview: async (
    reviewId: number,
    payload: { overall_score: number; summary?: string }
  ): Promise<ProposalReview> => {
    const { data } = await api.patch(
      `/reviews/${reviewId}/complete`,
      payload
    );
    return data;
  },
};
