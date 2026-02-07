import { render, screen } from "@testing-library/react";
import OpportunitiesPage from "@/app/(dashboard)/opportunities/page";
import { rfpApi, ingestApi, savedSearchApi } from "@/lib/api";
import { vi } from "vitest";

vi.mock("@/lib/api", () => ({
  rfpApi: {
    list: vi.fn(),
    getStats: vi.fn(),
  },
  savedSearchApi: {
    list: vi.fn(),
    create: vi.fn(),
    run: vi.fn(),
  },
  ingestApi: {
    triggerSamSearch: vi.fn(),
    getTaskStatus: vi.fn(),
  },
}));

const mockedRfpApi = vi.mocked(rfpApi);
const mockedIngestApi = vi.mocked(ingestApi);
const mockedSavedSearchApi = vi.mocked(savedSearchApi);

describe("OpportunitiesPage", () => {
  beforeEach(() => {
    mockedRfpApi.list.mockResolvedValue([
      {
        id: 1,
        title: "Test Cybersecurity Services RFP",
        solicitation_number: "W912HV-24-R-0001",
        agency: "Department of Defense",
        status: "new",
        is_qualified: true,
        qualification_score: 92,
        response_deadline: "2026-03-15T17:00:00Z",
        created_at: "2026-02-01T12:00:00Z",
      },
    ]);

    mockedRfpApi.getStats.mockResolvedValue({
      total: 1,
      qualified: 1,
      disqualified: 0,
      pending_filter: 0,
      by_status: { analyzing: 0 },
    });

    mockedSavedSearchApi.list.mockResolvedValue([]);

    mockedIngestApi.triggerSamSearch.mockResolvedValue({ task_id: "task-1", message: "Search started", status: "pending" });
    mockedIngestApi.getTaskStatus.mockResolvedValue({ task_id: "task-1", status: "completed" });
  });

  it("renders the opportunities list and stats", async () => {
    render(<OpportunitiesPage />);

    expect(
      await screen.findByText("Track and manage government contract opportunities")
    ).toBeInTheDocument();

    expect(
      await screen.findByText("Test Cybersecurity Services RFP")
    ).toBeInTheDocument();

    expect(await screen.findByText("Total RFPs")).toBeInTheDocument();
    expect(await screen.findByText("Qualified")).toBeInTheDocument();
    expect(await screen.findByText("Sync SAM.gov")).toBeInTheDocument();
  });

  it("shows an error state when loading fails", async () => {
    mockedRfpApi.list.mockRejectedValueOnce(new Error("Network error"));
    mockedRfpApi.getStats.mockRejectedValueOnce(new Error("Network error"));

    render(<OpportunitiesPage />);

    expect(
      await screen.findByText("Failed to load opportunities. Please try again.")
    ).toBeInTheDocument();

    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
