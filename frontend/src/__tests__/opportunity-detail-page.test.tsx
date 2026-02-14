import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import OpportunityDetailPage from "@/app/(dashboard)/opportunities/[rfpId]/page";
import { awardApi, contactApi, rfpApi, budgetIntelApi } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useParams: () => ({ rfpId: "1" }),
}));

vi.mock("@/lib/api", () => ({
  rfpApi: {
    get: vi.fn(),
    getSnapshots: vi.fn(),
    getSnapshotDiff: vi.fn(),
    getSnapshotAmendmentImpact: vi.fn(),
    update: vi.fn(),
  },
  awardApi: {
    list: vi.fn(),
    create: vi.fn(),
  },
  contactApi: {
    list: vi.fn(),
    create: vi.fn(),
  },
  budgetIntelApi: {
    list: vi.fn(),
    create: vi.fn(),
  },
}));

const mockedRfpApi = vi.mocked(rfpApi);
const mockedAwardApi = vi.mocked(awardApi);
const mockedContactApi = vi.mocked(contactApi);
const mockedBudgetApi = vi.mocked(budgetIntelApi);

describe("OpportunityDetailPage", () => {
  beforeEach(() => {
    mockedRfpApi.get.mockResolvedValue({
      id: 1,
      user_id: 1,
      title: "Test Opportunity",
      solicitation_number: "W912HV-24-R-0001",
      agency: "Department of Defense",
      rfp_type: "solicitation",
      status: "new",
      posted_date: "2026-02-01T00:00:00Z",
      response_deadline: "2026-03-15T17:00:00Z",
      source_url: "https://example.com",
      sam_gov_link: "https://sam.gov/example",
      summary: "Test summary",
      description: "Test description",
      is_qualified: true,
      qualification_score: 90,
      estimated_value: 250000,
      place_of_performance: "Remote",
      created_at: "2026-02-01T00:00:00Z",
      updated_at: "2026-02-02T00:00:00Z",
    });

    mockedRfpApi.getSnapshots.mockResolvedValue([
      {
        id: 10,
        notice_id: "NOTICE-10",
        solicitation_number: "W912HV-24-R-0001",
        rfp_id: 1,
        user_id: 1,
        fetched_at: "2026-02-02T00:00:00Z",
        posted_date: "2026-02-01T00:00:00Z",
        response_deadline: "2026-03-15T17:00:00Z",
        raw_hash: "hash-10",
        summary: {
          title: "Test Opportunity",
          agency: "Department of Defense",
          naics_code: "541519",
          response_deadline: "2026-03-15T17:00:00Z",
          resource_links_count: 2,
        },
      },
      {
        id: 9,
        notice_id: "NOTICE-09",
        solicitation_number: "W912HV-24-R-0001",
        rfp_id: 1,
        user_id: 1,
        fetched_at: "2026-02-01T00:00:00Z",
        posted_date: "2026-01-30T00:00:00Z",
        response_deadline: "2026-03-10T17:00:00Z",
        raw_hash: "hash-09",
        summary: {
          title: "Test Opportunity",
          agency: "Department of Defense",
          naics_code: "541512",
          response_deadline: "2026-03-10T17:00:00Z",
          resource_links_count: 1,
        },
      },
    ]);

    mockedRfpApi.getSnapshotDiff.mockResolvedValue({
      from_snapshot_id: 9,
      to_snapshot_id: 10,
      changes: [
        {
          field: "naics_code",
          before: "541512",
          after: "541519",
        },
      ],
      summary_from: {},
      summary_to: {},
    });
    mockedRfpApi.getSnapshotAmendmentImpact.mockResolvedValue({
      rfp_id: 1,
      from_snapshot_id: 9,
      to_snapshot_id: 10,
      generated_at: "2026-02-14T00:00:00Z",
      amendment_risk_level: "high",
      changed_fields: ["naics_code"],
      signals: [
        {
          field: "naics_code",
          from_value: "541512",
          to_value: "541519",
          impact_area: "eligibility",
          severity: "high",
          recommended_actions: ["Re-check NAICS alignment."],
        },
      ],
      impacted_sections: [
        {
          proposal_id: 12,
          proposal_title: "DoD Cyber Proposal",
          section_id: 41,
          section_number: "2.1",
          section_title: "Eligibility and Compliance",
          section_status: "approved",
          impact_score: 83,
          impact_level: "high",
          matched_change_fields: ["naics_code"],
          rationale: "NAICS references detected.",
          proposed_patch: "Update section language with amended NAICS.",
          recommended_actions: ["Re-check NAICS alignment."],
          approval_required: true,
        },
      ],
      summary: {
        changed_fields: 1,
        impacted_sections: 1,
        high_impact_sections: 1,
        medium_impact_sections: 0,
        low_impact_sections: 0,
        risk_level: "high",
      },
      approval_workflow: ["1) Review", "2) Patch", "3) Approve"],
    });
    mockedAwardApi.list.mockResolvedValue([]);
    mockedContactApi.list.mockResolvedValue([]);
    mockedBudgetApi.list.mockResolvedValue([]);
  });

  it("renders opportunity details and snapshot diff", async () => {
    const user = userEvent.setup();
    render(<OpportunityDetailPage />);

    expect(await screen.findByText("Test Opportunity")).toBeInTheDocument();
    expect(await screen.findByText("Opportunity Details")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Changes" }));
    expect(await screen.findByText("Snapshot Diff")).toBeInTheDocument();
    expect(await screen.findByText("naics_code")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Generate Impact Map" }));
    expect(await screen.findByText("Amendment Autopilot")).toBeInTheDocument();
    expect(await screen.findByText(/DoD Cyber Proposal/)).toBeInTheDocument();
    expect(await screen.findByText(/Risk:/)).toBeInTheDocument();
  });
});
