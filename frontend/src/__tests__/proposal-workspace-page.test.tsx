import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import ProposalWorkspacePage from "@/app/(dashboard)/proposals/[proposalId]/page";
import { draftApi, documentApi, wordAddinApi, graphicsApi } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useParams: () => ({ proposalId: "1" }),
}));

vi.mock("@/lib/api", () => ({
  draftApi: {
    getProposal: vi.fn(),
    listSections: vi.fn(),
    listSubmissionPackages: vi.fn(),
    listSectionEvidence: vi.fn(),
    updateSection: vi.fn(),
    addSectionEvidence: vi.fn(),
    createSubmissionPackage: vi.fn(),
  },
  documentApi: {
    list: vi.fn(),
  },
  exportApi: {
    exportProposalDocx: vi.fn(),
    exportProposalPdf: vi.fn(),
  },
  wordAddinApi: {
    listSessions: vi.fn(),
    createSession: vi.fn(),
    updateSession: vi.fn(),
    createEvent: vi.fn(),
    listEvents: vi.fn(),
  },
  graphicsApi: {
    listRequests: vi.fn(),
  },
}));

const mockedDraftApi = vi.mocked(draftApi);
const mockedDocumentApi = vi.mocked(documentApi);
const mockedWordAddinApi = vi.mocked(wordAddinApi);
const mockedGraphicsApi = vi.mocked(graphicsApi);

describe("ProposalWorkspacePage", () => {
  beforeEach(() => {
    mockedDraftApi.getProposal.mockResolvedValue({
      id: 1,
      user_id: 1,
      rfp_id: 1,
      title: "Test Proposal",
      version: 1,
      status: "draft",
      total_sections: 1,
      completed_sections: 0,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-02T00:00:00Z",
      completion_percentage: 0,
    });
    mockedDraftApi.listSections.mockResolvedValue([
      {
        id: 1,
        proposal_id: 1,
        title: "Section One",
        section_number: "1.0",
        status: "pending",
        display_order: 0,
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:00Z",
      },
    ]);
    mockedDraftApi.listSubmissionPackages.mockResolvedValue([]);
    mockedDraftApi.listSectionEvidence.mockResolvedValue([]);
    mockedDocumentApi.list.mockResolvedValue([]);
    mockedWordAddinApi.listSessions.mockResolvedValue([]);
    mockedGraphicsApi.listRequests.mockResolvedValue([]);
  });

  it("renders proposal workspace header", async () => {
    render(<ProposalWorkspacePage />);
    expect(await screen.findByText("Test Proposal")).toBeInTheDocument();
    expect(await screen.findByText("Sections")).toBeInTheDocument();
  });
});
