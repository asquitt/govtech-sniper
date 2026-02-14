import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import TeamingBoardPage from "@/app/(dashboard)/teaming/page";
import { teamingBoardApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  teamingBoardApi: {
    searchPartners: vi.fn(),
    listRequests: vi.fn(),
    getRequestFitTrends: vi.fn(),
    getPartnerTrends: vi.fn(),
    getPartnerCohorts: vi.fn(),
    getDigestSchedule: vi.fn(),
    updateDigestSchedule: vi.fn(),
    sendDigest: vi.fn(),
    exportRequestAuditCsv: vi.fn(),
    sendRequest: vi.fn(),
    updateRequest: vi.fn(),
    getGapAnalysis: vi.fn(),
  },
}));

const mockedTeamingApi = vi.mocked(teamingBoardApi);

describe("TeamingBoardPage fit analysis", () => {
  it("renders partner-fit rationale from gap analysis results", async () => {
    const createObjectUrl = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:teaming-audit");
    const revokeObjectUrl = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

    mockedTeamingApi.searchPartners.mockResolvedValue([
      {
        id: 12,
        name: "Fit Partner Co",
        partner_type: "sub",
        contact_name: "Jordan",
        contact_email: "jordan@fitpartner.com",
        company_duns: null,
        cage_code: null,
        naics_codes: ["541512"],
        set_asides: [],
        capabilities: ["Cloud migration"],
        clearance_level: "Secret",
        past_performance_summary: null,
        website: null,
      },
    ]);
    mockedTeamingApi.listRequests.mockResolvedValue([]);
    mockedTeamingApi.getRequestFitTrends.mockResolvedValue({
      days: 30,
      total_sent: 1,
      accepted_count: 1,
      declined_count: 0,
      pending_count: 0,
      acceptance_rate: 100,
      points: [
        {
          date: "2026-02-10",
          sent_count: 1,
          accepted_count: 1,
          declined_count: 0,
          fit_score: 100,
        },
      ],
    });
    mockedTeamingApi.getPartnerTrends.mockResolvedValue({
      days: 30,
      partners: [
        {
          partner_id: 12,
          partner_name: "Fit Partner Co",
          sent_count: 1,
          accepted_count: 1,
          declined_count: 0,
          pending_count: 0,
          acceptance_rate: 100,
          avg_response_hours: 2,
        },
      ],
    });
    mockedTeamingApi.getPartnerCohorts.mockResolvedValue({
      days: 30,
      total_sent: 1,
      naics_cohorts: [
        {
          cohort_value: "541512",
          partner_count: 1,
          sent_count: 1,
          accepted_count: 1,
          declined_count: 0,
          pending_count: 0,
          acceptance_rate: 100,
        },
      ],
      set_aside_cohorts: [
        {
          cohort_value: "8a",
          partner_count: 1,
          sent_count: 1,
          accepted_count: 1,
          declined_count: 0,
          pending_count: 0,
          acceptance_rate: 100,
        },
      ],
    });
    mockedTeamingApi.getDigestSchedule.mockResolvedValue({
      frequency: "weekly",
      day_of_week: 1,
      hour_utc: 14,
      minute_utc: 0,
      channel: "in_app",
      include_declined_reasons: true,
      is_enabled: true,
      last_sent_at: null,
    });
    mockedTeamingApi.exportRequestAuditCsv.mockResolvedValue(
      new Blob(["request_id,event_type"], { type: "text/csv" })
    );
    mockedTeamingApi.getGapAnalysis.mockResolvedValue({
      rfp_id: 22,
      analysis_summary: "One technical gap identified with partner recommendations.",
      gaps: [
        {
          gap_type: "technical",
          description: "Cloud migration expertise required",
          required_value: "AWS/Azure migration",
          matching_partner_ids: [12],
        },
      ],
      recommended_partners: [
        {
          partner_id: 12,
          name: "Fit Partner Co",
          reason: "Capability match",
        },
      ],
    });

    render(<TeamingBoardPage />);

    expect(await screen.findByText("Fit Partner Co")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("RFP ID"), { target: { value: "22" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze Fit" }));

    await waitFor(() => expect(mockedTeamingApi.getGapAnalysis).toHaveBeenCalledWith(22));
    expect(await screen.findByText("Fit rationale")).toBeInTheDocument();
    expect(
      await screen.findByText("Recommendation: Capability match")
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Sent \(/ }));
    expect(await screen.findByTestId("teaming-acceptance-rate")).toHaveTextContent("100%");
    expect(await screen.findByText("NAICS Cohorts")).toBeInTheDocument();
    expect(await screen.findByText(/541512:/)).toBeInTheDocument();
    expect(await screen.findByText("Set-Aside Cohorts")).toBeInTheDocument();
    expect(await screen.findByText(/8a:/)).toBeInTheDocument();
    fireEvent.click(await screen.findByTestId("teaming-export-audit"));
    await waitFor(() =>
      expect(mockedTeamingApi.exportRequestAuditCsv).toHaveBeenCalledWith("sent", 30)
    );

    createObjectUrl.mockRestore();
    revokeObjectUrl.mockRestore();
  });
});
