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
  });
});
