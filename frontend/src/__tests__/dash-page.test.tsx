import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import DashPage from "@/app/(dashboard)/dash/page";
import { dashApi, rfpApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  dashApi: {
    ask: vi.fn(),
  },
  rfpApi: {
    list: vi.fn(),
  },
}));

const mockedDashApi = vi.mocked(dashApi);
const mockedRfpApi = vi.mocked(rfpApi);

describe("DashPage", () => {
  beforeEach(() => {
    mockedDashApi.ask.mockResolvedValue({
      answer: "Mocked answer",
      citations: [],
    });
    mockedRfpApi.list.mockResolvedValue([]);
  });

  it("renders Dash header", async () => {
    render(<DashPage />);
    expect(
      await screen.findByText("Your AI assistant for GovCon workflows")
    ).toBeInTheDocument();
    expect(await screen.findByText("Opportunity Context")).toBeInTheDocument();
  });
});
