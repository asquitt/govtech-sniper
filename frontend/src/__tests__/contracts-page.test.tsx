import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import ContractsPage from "@/app/(dashboard)/contracts/page";
import { contractApi, documentApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  contractApi: {
    list: vi.fn(),
    listDeliverables: vi.fn(),
    listTasks: vi.fn(),
    listModifications: vi.fn(),
    listCLINs: vi.fn(),
    listCPARS: vi.fn(),
    listCPARSEvidence: vi.fn(),
    listStatusReports: vi.fn(),
    create: vi.fn(),
    createDeliverable: vi.fn(),
    createTask: vi.fn(),
    createModification: vi.fn(),
    deleteModification: vi.fn(),
    createCLIN: vi.fn(),
    updateCLIN: vi.fn(),
    deleteCLIN: vi.fn(),
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
    mockedContractApi.listModifications.mockResolvedValue([]);
    mockedContractApi.listCLINs.mockResolvedValue([]);
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

  it("renders parent-child hierarchy metadata for selected contract", async () => {
    mockedContractApi.list.mockResolvedValue({
      contracts: [
        {
          id: 1,
          user_id: 1,
          contract_number: "CN-001",
          title: "Prime Contract",
          contract_type: "prime",
          status: "active",
          created_at: "2026-02-10T00:00:00Z",
          updated_at: "2026-02-10T00:00:00Z",
        },
        {
          id: 2,
          user_id: 1,
          contract_number: "CN-001-TO-01",
          title: "Task Order 1",
          parent_contract_id: 1,
          contract_type: "task_order",
          status: "active",
          created_at: "2026-02-10T00:00:00Z",
          updated_at: "2026-02-10T00:00:00Z",
        },
      ],
      total: 2,
    });

    render(<ContractsPage />);

    expect(await screen.findByText("Hierarchy")).toBeInTheDocument();
    expect(await screen.findByText("Parent Contract")).toBeInTheDocument();
    expect(await screen.findAllByText("Top-level contract")).toHaveLength(2);
    expect(await screen.findByText(/Parent: CN-001/)).toBeInTheDocument();
    expect(await screen.findByText(/CN-001-TO-01 - Task Order 1/)).toBeInTheDocument();
  });
});
