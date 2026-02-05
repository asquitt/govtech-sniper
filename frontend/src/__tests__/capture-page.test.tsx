import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import CapturePage from "@/app/(dashboard)/capture/page";
import { captureApi, rfpApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  captureApi: {
    listPlans: vi.fn(),
    createPlan: vi.fn(),
    updatePlan: vi.fn(),
  },
  rfpApi: {
    list: vi.fn(),
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
    mockedCaptureApi.listPlans.mockResolvedValue([]);
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
