import { render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import ReviewsPage from "@/app/(dashboard)/reviews/page";
import { reviewApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  reviewApi: {
    getDashboard: vi.fn(),
    getReviewPacket: vi.fn(),
  },
}));

const mockedReviewApi = vi.mocked(reviewApi);

describe("ReviewsPage", () => {
  beforeEach(() => {
    mockedReviewApi.getDashboard.mockResolvedValue([
      {
        review_id: 7,
        proposal_id: 12,
        proposal_title: "Cloud Modernization Proposal",
        review_type: "red",
        status: "in_progress",
        scheduled_date: "2026-02-20T00:00:00Z",
        overall_score: null,
        go_no_go_decision: null,
        total_comments: 3,
        open_comments: 2,
        total_assignments: 2,
        completed_assignments: 1,
      },
    ]);
    mockedReviewApi.getReviewPacket.mockResolvedValue({
      review_id: 7,
      proposal_id: 12,
      proposal_title: "Cloud Modernization Proposal",
      review_type: "red",
      review_status: "in_progress",
      generated_at: "2026-02-14T00:00:00Z",
      checklist_summary: {
        total_items: 6,
        pass_count: 4,
        fail_count: 1,
        pending_count: 1,
        na_count: 0,
        pass_rate: 66.7,
      },
      risk_summary: {
        open_critical: 1,
        open_major: 1,
        unresolved_comments: 2,
        highest_risk_score: 94.5,
        overall_risk_level: "high",
      },
      action_queue: [
        {
          rank: 1,
          comment_id: 19,
          section_id: 3,
          severity: "critical",
          status: "open",
          risk_score: 94.5,
          age_days: 2,
          assigned_to_user_id: null,
          recommended_action: "Assign immediate owner and patch before next review gate.",
          rationale: "Critical severity with open status and age 2d.",
        },
      ],
      recommended_exit_criteria: [
        "Open critical findings at red exit must be 0 (current: 1).",
      ],
    });
  });

  it("renders review packet insights with risk-ranked action queue", async () => {
    render(<ReviewsPage />);

    expect(await screen.findByText("Review Packet Builder")).toBeInTheDocument();
    expect(await screen.findByText("Risk-Ranked Action Queue")).toBeInTheDocument();
    expect(screen.getByText("Assign immediate owner and patch before next review gate.")).toBeInTheDocument();

    await waitFor(() => {
      expect(mockedReviewApi.getReviewPacket).toHaveBeenCalledWith(7);
    });
  });
});
