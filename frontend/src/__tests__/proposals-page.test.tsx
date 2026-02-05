import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import ProposalsPage from "@/app/(dashboard)/proposals/page";
import { draftApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  draftApi: {
    listProposals: vi.fn(),
  },
}));

const mockedDraftApi = vi.mocked(draftApi);

describe("ProposalsPage", () => {
  beforeEach(() => {
    mockedDraftApi.listProposals.mockResolvedValue([]);
  });

  it("renders proposals header", async () => {
    render(<ProposalsPage />);
    expect(await screen.findByText("Manage proposal drafts")).toBeInTheDocument();
  });
});
