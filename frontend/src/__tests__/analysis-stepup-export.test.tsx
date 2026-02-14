import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import AnalysisPage from "@/app/(dashboard)/analysis/[rfpId]/page";
import { rfpApi, analysisApi, draftApi, exportApi } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useParams: () => ({ rfpId: "1" }),
}));

vi.mock("@/components/analysis/compliance-matrix", () => ({
  ComplianceMatrix: () => <div data-testid="compliance-matrix" />,
}));

vi.mock("@/components/analysis/draft-preview", () => ({
  DraftPreview: () => <div data-testid="draft-preview" />,
}));

vi.mock("@/app/(dashboard)/analysis/[rfpId]/_components/analysis-header", () => ({
  AnalysisHeader: ({ onExport }: { onExport: () => void }) => (
    <button onClick={onExport}>Export Proposal</button>
  ),
}));

vi.mock("@/app/(dashboard)/analysis/[rfpId]/_components/status-bar", () => ({
  StatusBar: () => <div data-testid="status-bar" />,
}));

vi.mock("@/app/(dashboard)/analysis/[rfpId]/_components/edit-requirement-form", () => ({
  EditRequirementForm: () => null,
  initEditForm: () => ({
    section: "",
    requirement_text: "",
    importance: "mandatory",
    category: "",
    notes: "",
    confidence: 0.5,
    status: "open",
  }),
}));

vi.mock("@/app/(dashboard)/analysis/[rfpId]/_components/create-requirement-form", () => ({
  CreateRequirementForm: () => null,
}));

vi.mock("@/app/(dashboard)/analysis/[rfpId]/_components/shred-view", () => ({
  ShredView: () => null,
}));

vi.mock("@/lib/api", () => ({
  rfpApi: {
    get: vi.fn(),
    getSnapshots: vi.fn(),
    getSnapshotDiff: vi.fn(),
  },
  analysisApi: {
    getComplianceMatrix: vi.fn(),
    updateRequirement: vi.fn(),
  },
  draftApi: {
    listProposals: vi.fn(),
  },
  exportApi: {
    exportProposalDocx: vi.fn(),
  },
}));

const mockedRfpApi = vi.mocked(rfpApi);
const mockedAnalysisApi = vi.mocked(analysisApi);
const mockedDraftApi = vi.mocked(draftApi);
const mockedExportApi = vi.mocked(exportApi);

describe("AnalysisPage export step-up flow", () => {
  beforeEach(() => {
    mockedRfpApi.get.mockResolvedValue({
      id: 1,
      user_id: 1,
      title: "Analysis RFP",
      solicitation_number: "SOL-001",
      agency: "Agency",
      status: "analyzed",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    mockedRfpApi.getSnapshots.mockResolvedValue([]);
    mockedAnalysisApi.getComplianceMatrix.mockResolvedValue({
      requirements: [],
      generated_at: "2026-01-01T00:00:00Z",
    });
    mockedDraftApi.listProposals.mockResolvedValue([{ id: 99 }]);
    mockedExportApi.exportProposalDocx.mockResolvedValue(new Blob(["docx"]));
  });

  it("opens MFA modal when export requires step-up and retries with code", async () => {
    const createObjectUrl = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:analysis");
    const revokeObjectUrl = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    mockedExportApi.exportProposalDocx
      .mockRejectedValueOnce({
        response: { headers: { "x-step-up-required": "true" } },
      })
      .mockResolvedValueOnce(new Blob(["docx"]));

    render(<AnalysisPage />);
    await screen.findByText("Export Proposal");

    fireEvent.click(screen.getByRole("button", { name: "Export Proposal" }));

    await screen.findByText("Step-Up Authentication Required");
    fireEvent.change(screen.getByLabelText("Step-up authentication code"), {
      target: { value: "654321" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() =>
      expect(mockedExportApi.exportProposalDocx).toHaveBeenCalledWith(99, "654321")
    );

    createObjectUrl.mockRestore();
    revokeObjectUrl.mockRestore();
  });
});
