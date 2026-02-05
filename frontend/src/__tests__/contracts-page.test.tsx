import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import ContractsPage from "@/app/(dashboard)/contracts/page";
import { contractApi, documentApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  contractApi: {
    list: vi.fn(),
    listDeliverables: vi.fn(),
    listTasks: vi.fn(),
    listCPARS: vi.fn(),
    listCPARSEvidence: vi.fn(),
    listStatusReports: vi.fn(),
    create: vi.fn(),
    createDeliverable: vi.fn(),
    createTask: vi.fn(),
    createCPARS: vi.fn(),
    addCPARSEvidence: vi.fn(),
    deleteCPARSEvidence: vi.fn(),
    createStatusReport: vi.fn(),
  },
  documentApi: {
    list: vi.fn(),
  },
}));

const mockedContractApi = vi.mocked(contractApi);
const mockedDocumentApi = vi.mocked(documentApi);

describe("ContractsPage", () => {
  beforeEach(() => {
    mockedContractApi.list.mockResolvedValue({ contracts: [], total: 0 });
    mockedContractApi.listDeliverables.mockResolvedValue([]);
    mockedContractApi.listTasks.mockResolvedValue([]);
    mockedContractApi.listCPARS.mockResolvedValue([]);
    mockedContractApi.listCPARSEvidence.mockResolvedValue([]);
    mockedContractApi.listStatusReports.mockResolvedValue([]);
    mockedDocumentApi.list.mockResolvedValue([]);
  });

  it("renders contracts header", async () => {
    render(<ContractsPage />);
    expect(
      await screen.findByText("Track post-award execution and deliverables")
    ).toBeInTheDocument();
  });
});
