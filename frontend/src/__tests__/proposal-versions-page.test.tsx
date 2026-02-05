import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import ProposalVersionsPage from "@/app/(dashboard)/proposals/[proposalId]/versions/page";
import { draftApi, versionApi } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useParams: () => ({ proposalId: "1" }),
}));

vi.mock("@/lib/api", () => ({
  draftApi: {
    getProposal: vi.fn(),
  },
  versionApi: {
    listProposalVersions: vi.fn(),
    getProposalVersion: vi.fn(),
  },
}));

const mockedDraftApi = vi.mocked(draftApi);
const mockedVersionApi = vi.mocked(versionApi);

describe("ProposalVersionsPage", () => {
  beforeEach(() => {
    mockedDraftApi.getProposal.mockResolvedValue({
      id: 1,
      user_id: 1,
      rfp_id: 1,
      title: "Test Proposal",
      version: 3,
      status: "draft",
      executive_summary: null,
      total_sections: 5,
      completed_sections: 2,
      compliance_score: 78,
      docx_export_path: null,
      pdf_export_path: null,
      created_at: "2026-02-01T00:00:00Z",
      updated_at: "2026-02-02T00:00:00Z",
      submitted_at: null,
      completion_percentage: 40,
    });

    mockedVersionApi.listProposalVersions.mockResolvedValue([
      {
        id: 10,
        proposal_id: 1,
        version_number: 3,
        version_type: "manual",
        description: "Initial submission",
        user_id: 1,
        created_at: "2026-02-03T00:00:00Z",
        has_snapshot: true,
      },
    ]);

    mockedVersionApi.getProposalVersion.mockResolvedValue({
      id: 10,
      proposal_id: 1,
      version_number: 3,
      version_type: "manual",
      description: "Initial submission",
      user_id: 1,
      created_at: "2026-02-03T00:00:00Z",
      has_snapshot: true,
      snapshot: {
        title: "Test Proposal",
        status: "draft",
        total_sections: 5,
        completed_sections: 2,
        compliance_score: 78,
      },
    });
  });

  it("renders proposal version history", async () => {
    render(<ProposalVersionsPage />);

    expect(await screen.findByText("Proposal Versions")).toBeInTheDocument();
    expect(await screen.findByText("Version 3")).toBeInTheDocument();
    expect(await screen.findByText("Proposal Snapshot")).toBeInTheDocument();
  });
});
