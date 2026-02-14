import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import OpportunitiesPage from "@/app/(dashboard)/opportunities/page";
import { rfpApi, ingestApi, savedSearchApi } from "@/lib/api";
import { vi } from "vitest";

vi.mock("@/lib/api", () => ({
  rfpApi: {
    list: vi.fn(),
    getStats: vi.fn(),
    create: vi.fn(),
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
    mockedRfpApi.create.mockResolvedValue({
      id: 2,
      title: "Created RFP",
      solicitation_number: "CREATED-001",
      agency: "GSA",
      status: "new",
      is_qualified: null,
      qualification_score: null,
      response_deadline: null,
      created_at: "2026-02-01T12:00:00Z",
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

    expect(await screen.findByRole("button", { name: "Refresh" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Add RFP" })).toBeInTheDocument();
  });

  it("keeps primary actions available when SAM sync fails", async () => {
    mockedIngestApi.triggerSamSearch.mockRejectedValueOnce({
      response: {
        data: {
          detail: "SAM.gov rate limit reached. Retry in about 60 seconds.",
        },
      },
    });

    render(<OpportunitiesPage />);
    await screen.findByText("Track and manage government contract opportunities");

    await userEvent.click(screen.getByRole("button", { name: "Sync SAM.gov" }));

    expect(
      await screen.findByText("SAM.gov rate limit reached. Retry in about 60 seconds.")
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add RFP" })).toBeInTheDocument();
  });

  it("disables sync during Retry-After cooldown", async () => {
    mockedIngestApi.triggerSamSearch.mockRejectedValueOnce({
      response: {
        data: {
          detail: "SAM.gov rate limit reached. Retry in about 90 seconds.",
        },
        headers: {
          "retry-after": "90",
        },
      },
    });

    render(<OpportunitiesPage />);
    await screen.findByText("Track and manage government contract opportunities");

    await userEvent.click(screen.getByRole("button", { name: "Sync SAM.gov" }));

    const cooldownButton = await screen.findByRole("button", { name: /Sync in/i });
    expect(cooldownButton).toBeDisabled();
  });

  it("allows manually creating an RFP from the opportunities page", async () => {
    render(<OpportunitiesPage />);
    await screen.findByText("Track and manage government contract opportunities");

    await userEvent.click(screen.getByRole("button", { name: "Add RFP" }));

    await userEvent.type(screen.getByLabelText("Title"), "Manual Opportunity");
    await userEvent.type(screen.getByLabelText("Solicitation Number"), "MANUAL-001");
    await userEvent.type(screen.getByLabelText("Agency"), "General Services Administration");
    await userEvent.type(
      screen.getByLabelText("Description"),
      "Manual opportunity added while SAM.gov is unavailable."
    );

    await userEvent.click(screen.getByRole("button", { name: "Save RFP" }));

    expect(mockedRfpApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Manual Opportunity",
        solicitation_number: "MANUAL-001",
        agency: "General Services Administration",
        classification: "internal",
      })
    );
  });

  it("does not poll task status when ingest completes immediately", async () => {
    mockedIngestApi.triggerSamSearch.mockResolvedValueOnce({
      task_id: "sync-task-1",
      message: "Ingest completed synchronously",
      status: "completed",
    });

    render(<OpportunitiesPage />);
    await screen.findByText("Track and manage government contract opportunities");

    mockedIngestApi.getTaskStatus.mockClear();

    await userEvent.click(screen.getByRole("button", { name: "Sync SAM.gov" }));

    expect(mockedIngestApi.triggerSamSearch).toHaveBeenCalledTimes(1);
    expect(mockedIngestApi.getTaskStatus).not.toHaveBeenCalled();
  });

  it("falls back to showing all RFPs when recommended filter has no matches", async () => {
    mockedRfpApi.list.mockResolvedValueOnce([
      {
        id: 2,
        title: "Unqualified Legacy Support RFP",
        solicitation_number: "LEGACY-0002",
        agency: "Department of Legacy Systems",
        status: "new",
        is_qualified: false,
        qualification_score: 22,
        response_deadline: "2026-03-20T17:00:00Z",
        created_at: "2026-02-02T12:00:00Z",
      },
    ]);
    mockedRfpApi.getStats.mockResolvedValueOnce({
      total: 1,
      qualified: 0,
      disqualified: 1,
      pending_filter: 0,
      by_status: { analyzing: 0 },
    });

    render(<OpportunitiesPage />);

    expect(
      await screen.findByText("Unqualified Legacy Support RFP")
    ).toBeInTheDocument();
  });

  it("passes source, jurisdiction, and currency filters to list API", async () => {
    render(<OpportunitiesPage />);
    await screen.findByText("Track and manage government contract opportunities");

    await userEvent.click(screen.getByRole("button", { name: "Filters" }));
    await userEvent.selectOptions(screen.getByLabelText("Source Type"), "canada_provincial");
    await userEvent.selectOptions(screen.getByLabelText("Jurisdiction"), "CA-ON");
    await userEvent.selectOptions(screen.getByLabelText("Currency"), "CAD");

    await waitFor(() => {
      expect(mockedRfpApi.list).toHaveBeenLastCalledWith({
        source_type: "canada_provincial",
        jurisdiction: "CA-ON",
        currency: "CAD",
      });
    });
  });
});
