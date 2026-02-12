import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GlobalSearch } from "@/components/layout/global-search";
import { searchApi } from "@/lib/api/search";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/api/search", () => ({
  searchApi: {
    search: vi.fn(),
  },
}));

describe("GlobalSearch", () => {
  beforeEach(() => {
    vi.mocked(searchApi.search).mockResolvedValue({
      data: {
        query: "cyber",
        total: 1,
        results: [
          {
            entity_type: "rfp",
            entity_id: 42,
            chunk_text: "Cybersecurity modernization support",
            score: 0.95,
            chunk_index: 0,
          },
        ],
      },
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("opens with keyboard shortcut, searches, and navigates result", async () => {
    render(<GlobalSearch />);

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });

    const input = await screen.findByTestId("global-search-input");
    fireEvent.change(input, { target: { value: "cyber" } });

    await waitFor(() => expect(searchApi.search).toHaveBeenCalled());
    expect(searchApi.search).toHaveBeenLastCalledWith({
      query: "cyber",
      limit: 10,
      entity_types: undefined,
    });

    fireEvent.click(await screen.findByText(/Cybersecurity modernization support/i));
    expect(pushMock).toHaveBeenCalledWith("/opportunities/42");
  });

  it("applies entity facets to search payload", async () => {
    render(<GlobalSearch />);

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const input = await screen.findByTestId("global-search-input");
    fireEvent.change(input, { target: { value: "cyber" } });
    await waitFor(() => expect(searchApi.search).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Opportunities" }));
    fireEvent.click(screen.getByRole("button", { name: "Proposal Sections" }));
    fireEvent.click(screen.getByRole("button", { name: "Knowledge Base" }));

    await waitFor(() =>
      expect(searchApi.search).toHaveBeenLastCalledWith(
        expect.objectContaining({ entity_types: ["contact"] })
      )
    );
  });
});
