import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import DashPage from "@/app/(dashboard)/dash/page";
import { dashApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  dashApi: {
    ask: vi.fn(),
  },
}));

const mockedDashApi = vi.mocked(dashApi);

describe("DashPage", () => {
  beforeEach(() => {
    mockedDashApi.ask.mockResolvedValue({
      answer: "Mocked answer",
      citations: [],
    });
  });

  it("renders Dash header", async () => {
    render(<DashPage />);
    expect(
      await screen.findByText("Your AI assistant for GovCon workflows")
    ).toBeInTheDocument();
  });
});
