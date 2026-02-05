import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import CapturePage from "@/app/(dashboard)/capture/page";
import { captureApi, rfpApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  captureApi: {
    listPlans: vi.fn(),
    createPlan: vi.fn(),
    updatePlan: vi.fn(),
    listFields: vi.fn(),
    createField: vi.fn(),
    listPlanFields: vi.fn(),
    savePlanFields: vi.fn(),
    listPartners: vi.fn(),
    listPartnerLinks: vi.fn(),
    listGateReviews: vi.fn(),
    listCompetitors: vi.fn(),
    getMatchInsight: vi.fn(),
    createCompetitor: vi.fn(),
    removeCompetitor: vi.fn(),
  },
  rfpApi: {
    list: vi.fn(),
    get: vi.fn(),
  },
}));

const mockedCaptureApi = vi.mocked(captureApi);
const mockedRfpApi = vi.mocked(rfpApi);

describe("CapturePage", () => {
  beforeEach(() => {
    mockedRfpApi.list.mockResolvedValue([
      {
        id: 1,
        title: "Test RFP",
        solicitation_number: "SOL-001",
        agency: "Test Agency",
        status: "new",
        created_at: "2026-02-01T00:00:00Z",
      },
    ]);
    mockedRfpApi.get.mockResolvedValue({
      id: 1,
      user_id: 1,
      title: "Test RFP",
      solicitation_number: "SOL-001",
      agency: "Test Agency",
      rfp_type: "solicitation",
      status: "new",
      posted_date: "2026-02-01T00:00:00Z",
      response_deadline: "2026-03-01T00:00:00Z",
      source_type: "federal",
      jurisdiction: "VA",
      contract_vehicle: "SEWP",
      incumbent_vendor: "Incumbent Co",
      buyer_contact_name: "Alex Buyer",
      buyer_contact_email: "buyer@example.com",
      buyer_contact_phone: "555-123-4567",
      budget_estimate: 250000,
      competitive_landscape: "Known competitor activity.",
      intel_notes: "Watch for set-aside changes.",
      created_at: "2026-02-01T00:00:00Z",
      updated_at: "2026-02-02T00:00:00Z",
    });
    mockedCaptureApi.listPlans.mockResolvedValue([]);
    mockedCaptureApi.listFields.mockResolvedValue([]);
    mockedCaptureApi.listPlanFields.mockResolvedValue({ fields: [] });
    mockedCaptureApi.listPartners.mockResolvedValue([]);
    mockedCaptureApi.listPartnerLinks.mockResolvedValue({ links: [], total: 0 });
    mockedCaptureApi.listGateReviews.mockResolvedValue([]);
    mockedCaptureApi.listCompetitors.mockResolvedValue([]);
    mockedCaptureApi.getMatchInsight.mockResolvedValue({
      plan_id: 1,
      rfp_id: 1,
      summary: "Test summary",
      factors: [],
    });
  });

  it("renders capture pipeline header", async () => {
    render(<CapturePage />);
    expect(
      await screen.findByText(
        "Track bid decisions, gate reviews, and teaming partners"
      )
    ).toBeInTheDocument();
    expect(await screen.findByText("Capture Pipeline")).toBeInTheDocument();
  });
});
