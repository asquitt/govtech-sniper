import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import ProposalWorkspacePage from "@/app/(dashboard)/proposals/[proposalId]/page";
import {
  analysisApi,
  draftApi,
  documentApi,
  exportApi,
  wordAddinApi,
  graphicsApi,
} from "@/lib/api";

vi.mock("next/navigation", () => ({
  useParams: () => ({ proposalId: "1" }),
}));

vi.mock("@/components/proposals/rich-text-editor", () => ({
  RichTextEditor: ({
    content,
    onUpdate,
  }: {
    content: string;
    onUpdate: (value: string) => void;
  }) => (
    <textarea
      aria-label="Mock rich text editor"
      value={content}
      onChange={(event) => onUpdate(event.target.value)}
    />
  ),
}));

vi.mock("@/components/proposals/writing-plan-panel", () => ({
  WritingPlanPanel: () => <div>Writing Plan Panel</div>,
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
    getScorecard: vi.fn(),
    listFocusDocuments: vi.fn(),
    rewriteSection: vi.fn(),
    expandSection: vi.fn(),
  },
  documentApi: {
    list: vi.fn(),
  },
  exportApi: {
    exportProposalDocx: vi.fn(),
    exportProposalPdf: vi.fn(),
    exportCompliancePackage: vi.fn(),
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
    listTemplates: vi.fn(),
    generateGraphic: vi.fn(),
  },
  analysisApi: {
    getComplianceMatrix: vi.fn(),
  },
}));

const mockedAnalysisApi = vi.mocked(analysisApi);
const mockedDraftApi = vi.mocked(draftApi);
const mockedDocumentApi = vi.mocked(documentApi);
const mockedExportApi = vi.mocked(exportApi);
const mockedWordAddinApi = vi.mocked(wordAddinApi);
const mockedGraphicsApi = vi.mocked(graphicsApi);

describe("ProposalWorkspacePage", () => {
  beforeEach(() => {
    mockedExportApi.exportProposalDocx.mockResolvedValue(new Blob(["docx"]));
    mockedExportApi.exportProposalPdf.mockResolvedValue(new Blob(["pdf"]));
    mockedExportApi.exportCompliancePackage.mockResolvedValue(new Blob(["zip"]));
    mockedAnalysisApi.getComplianceMatrix.mockResolvedValue({
      requirements: [],
      generated_at: "2025-01-01T00:00:00Z",
    });
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
        final_content: "Initial technical approach content.",
        status: "pending",
        display_order: 0,
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:00Z",
      },
    ]);
    mockedDraftApi.listSubmissionPackages.mockResolvedValue([]);
    mockedDraftApi.listSectionEvidence.mockResolvedValue([]);
    mockedDraftApi.getScorecard.mockResolvedValue({
      proposal_id: 1,
      proposal_title: "Test Proposal",
      overall_score: null,
      sections_scored: 0,
      sections_total: 1,
      pink_team_ready: false,
      section_scores: [],
    });
    mockedDraftApi.listFocusDocuments.mockResolvedValue([]);
    mockedDocumentApi.list.mockResolvedValue([]);
    mockedWordAddinApi.listSessions.mockResolvedValue([]);
    mockedGraphicsApi.listRequests.mockResolvedValue([]);
    mockedGraphicsApi.listTemplates.mockResolvedValue([
      { type: "timeline", label: "Timeline" },
    ]);
    mockedGraphicsApi.generateGraphic.mockResolvedValue({
      mermaid_code: "flowchart TD\\nA-->B",
      template_type: "timeline",
      title: "Generated Graphic",
    });
  });

  it("renders proposal workspace header", async () => {
    render(<ProposalWorkspacePage />);
    expect(await screen.findByText("Test Proposal")).toBeInTheDocument();
    expect(await screen.findByText("Sections")).toBeInTheDocument();
  });

  it("opens MFA modal when export requires step-up and retries with code", async () => {
    const createObjectUrl = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:proposal");
    const revokeObjectUrl = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    mockedExportApi.exportProposalDocx
      .mockRejectedValueOnce({
        response: { headers: { "x-step-up-required": "true" } },
      })
      .mockResolvedValueOnce(new Blob(["docx"]));

    render(<ProposalWorkspacePage />);
    await screen.findByText("Test Proposal");

    fireEvent.click(screen.getByRole("button", { name: "Export DOCX" }));

    await screen.findByText("Step-Up Authentication Required");
    fireEvent.change(screen.getByLabelText("Step-up authentication code"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() =>
      expect(mockedExportApi.exportProposalDocx).toHaveBeenCalledWith(1, "123456")
    );

    createObjectUrl.mockRestore();
    revokeObjectUrl.mockRestore();
  });

  it("exports evidence bundle from workspace header", async () => {
    const createObjectUrl = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:bundle");
    const revokeObjectUrl = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

    render(<ProposalWorkspacePage />);
    await screen.findByText("Test Proposal");

    fireEvent.click(screen.getByRole("button", { name: "Export Evidence Bundle" }));

    await waitFor(() =>
      expect(mockedExportApi.exportCompliancePackage).toHaveBeenCalledWith(1, undefined)
    );

    createObjectUrl.mockRestore();
    revokeObjectUrl.mockRestore();
  });

  it("preserves AI suggestion markup after rewrite updates section metadata", async () => {
    const rewrittenText = "Rewritten proposal response with stronger compliance language.";
    mockedDraftApi.rewriteSection.mockResolvedValue({
      id: 1,
      proposal_id: 1,
      title: "Section One",
      section_number: "1.0",
      final_content: "Initial technical approach content.",
      generated_content: {
        raw_text: rewrittenText,
        clean_text: rewrittenText,
        citations: [],
        model_used: "mock",
        tokens_used: 12,
        generation_time_seconds: 0.2,
      },
      status: "editing",
      display_order: 0,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-02T00:00:00Z",
    });

    render(<ProposalWorkspacePage />);
    await screen.findByText("Test Proposal");

    fireEvent.click(screen.getByRole("button", { name: "Rewrite" }));
    fireEvent.click(screen.getByRole("button", { name: "professional" }));

    await waitFor(() =>
      expect(mockedDraftApi.rewriteSection).toHaveBeenCalledWith(1, { tone: "professional" })
    );

    await waitFor(() => {
      const editorValue = (screen.getByLabelText("Mock rich text editor") as HTMLTextAreaElement).value;
      expect(editorValue).toContain('data-ai-suggestion="true"');
      expect(editorValue).toContain(rewrittenText);
    });
  });
});
