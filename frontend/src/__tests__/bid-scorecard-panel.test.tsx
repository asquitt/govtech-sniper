import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import BidScorecardPanel from "@/app/(dashboard)/capture/_components/bid-scorecard-panel";
import { captureApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  captureApi: {
    listScorecards: vi.fn(),
    getBidSummary: vi.fn(),
    aiEvaluateBid: vi.fn(),
    simulateBidScenarios: vi.fn(),
  },
}));

const mockedCaptureApi = vi.mocked(captureApi);

describe("BidScorecardPanel", () => {
  beforeEach(() => {
    mockedCaptureApi.listScorecards.mockResolvedValue([
      {
        id: 1001,
        rfp_id: 12,
        overall_score: 76,
        recommendation: "bid",
        confidence: 0.82,
        reasoning: "Strong positioning with manageable risk.",
        scorer_type: "ai",
        scorer_id: null,
        criteria_scores: [
          { name: "technical_capability", weight: 15, score: 82 },
          { name: "past_performance", weight: 12, score: 78 },
        ],
        created_at: "2026-02-14T00:00:00Z",
      },
    ]);
    mockedCaptureApi.getBidSummary.mockResolvedValue({
      rfp_id: 12,
      total_votes: 1,
      ai_score: 76,
      human_avg: null,
      overall_recommendation: "bid",
      bid_count: 1,
      no_bid_count: 0,
      conditional_count: 0,
    });
    mockedCaptureApi.simulateBidScenarios.mockResolvedValue({
      rfp_id: 12,
      baseline: {
        scorecard_id: 1001,
        overall_score: 76,
        recommendation: "bid",
        confidence: 0.82,
        scoring_method: "Weighted-factor simulation aligned to FAR 15.305 and Section M factors",
        criteria_scores: [
          { name: "technical_capability", weight: 15, score: 82 },
          { name: "past_performance", weight: 12, score: 78 },
        ],
      },
      scenarios: [
        {
          name: "Severe Downside",
          notes: "Major negative shifts in incumbent pressure and staffing.",
          overall_score: 42,
          recommendation: "no_bid",
          confidence: 0.41,
          decision_risk: "high",
          risk_score: 0.78,
          recommendation_changed: true,
          criteria_scores: [],
          driver_summary: {
            positive: [],
            negative: [
              {
                name: "technical_capability",
                weight: 15,
                baseline_score: 82,
                scenario_score: 35,
                delta: -47,
                weighted_impact: -7.05,
                far_reference: "FAR 15.305(a)(3)",
                section_m_factor: "Technical approach and capability",
              },
            ],
          },
          scoring_rationale: {
            method: "Weighted-factor simulation aligned to FAR 15.305 and Section M factors",
            dominant_factors: [
              {
                criterion: "technical_capability",
                weighted_impact: -7.05,
                far_reference: "FAR 15.305(a)(3)",
                section_m_factor: "Technical approach and capability",
              },
            ],
          },
          ignored_adjustments: [],
        },
      ],
    });
  });

  it("runs stress-test simulation and renders calibrated scenario output", async () => {
    const user = userEvent.setup();
    render(<BidScorecardPanel rfpId={12} />);

    expect(await screen.findByText("Bid Decision Summary")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Run Scenario Simulator" }));

    await waitFor(() => {
      expect(mockedCaptureApi.simulateBidScenarios).toHaveBeenCalledWith(
        12,
        expect.objectContaining({
          scenarios: expect.any(Array),
        })
      );
    });

    expect(await screen.findByText("Scenario Results")).toBeInTheDocument();
    expect(screen.getByText("Severe Downside")).toBeInTheDocument();
    expect(screen.getByText("Recommendation changed from baseline")).toBeInTheDocument();
    expect(screen.getByText("High Risk")).toBeInTheDocument();
  });
});
