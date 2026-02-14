import { fireEvent, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import SignalsPage from "@/app/(dashboard)/signals/page";
import { signalApi } from "@/lib/api/signals";
import {
  useMarkSignalRead,
  useSignalFeed,
  useSignalSubscription,
  useUpsertSubscription,
} from "@/hooks/use-signals";
import { renderWithQueryClient } from "@/test/react-query";

vi.mock("@/components/layout/header", () => ({
  Header: ({ title, actions }: { title: string; actions?: unknown }) => (
    <div>
      <h1>{title}</h1>
      {actions as JSX.Element | null}
    </div>
  ),
}));

vi.mock("@/hooks/use-signals", () => ({
  useSignalFeed: vi.fn(),
  useSignalSubscription: vi.fn(),
  useMarkSignalRead: vi.fn(),
  useUpsertSubscription: vi.fn(),
}));

vi.mock("@/lib/api/signals", () => ({
  signalApi: {
    ingestNews: vi.fn(),
    ingestBudgetAnalysis: vi.fn(),
    rescore: vi.fn(),
    digestPreview: vi.fn(),
    sendDigest: vi.fn(),
  },
}));

const mockedSignalApi = vi.mocked(signalApi);

describe("SignalsPage", () => {
  beforeEach(() => {
    vi.mocked(useSignalFeed).mockReturnValue({
      data: {
        signals: [
          {
            id: 10,
            user_id: 1,
            title: "Cloud modernization budget signal",
            signal_type: "budget",
            agency: "DoD",
            content: "Budget update",
            source_url: null,
            relevance_score: 84,
            published_at: "2026-02-14T00:00:00",
            is_read: false,
            created_at: "2026-02-14T00:00:00",
          },
        ],
        total: 1,
      },
      isLoading: false,
    } as ReturnType<typeof useSignalFeed>);
    vi.mocked(useSignalSubscription).mockReturnValue({
      data: {
        id: 1,
        user_id: 1,
        agencies: ["DoD"],
        naics_codes: ["541512"],
        keywords: ["cloud", "modernization"],
        email_digest_enabled: true,
        digest_frequency: "daily",
        created_at: "2026-02-14T00:00:00",
        updated_at: "2026-02-14T00:00:00",
      },
    } as ReturnType<typeof useSignalSubscription>);
    vi.mocked(useMarkSignalRead).mockReturnValue({
      mutate: vi.fn(),
    } as ReturnType<typeof useMarkSignalRead>);
    vi.mocked(useUpsertSubscription).mockReturnValue({
      mutate: vi.fn(),
    } as ReturnType<typeof useUpsertSubscription>);

    mockedSignalApi.ingestNews.mockResolvedValue({
      created: 2,
      updated: 0,
      skipped: 1,
      source_breakdown: { fallback: 2 },
    });
    mockedSignalApi.ingestBudgetAnalysis.mockResolvedValue({
      created: 1,
      updated: 0,
      skipped: 0,
      source_breakdown: { budget_intelligence: 1 },
    });
    mockedSignalApi.rescore.mockResolvedValue({
      updated: 3,
      average_score: 78.3,
    });
    mockedSignalApi.digestPreview.mockResolvedValue({
      period_days: 1,
      total_unread: 3,
      included_count: 2,
      type_breakdown: { budget: 1, news: 1 },
      top_signals: [
        {
          signal_id: 10,
          title: "Cloud modernization budget signal",
          signal_type: "budget",
          agency: "DoD",
          relevance_score: 84,
          source_url: null,
          published_at: "2026-02-14T00:00:00",
        },
      ],
    });
    mockedSignalApi.sendDigest.mockResolvedValue({
      period_days: 1,
      total_unread: 3,
      included_count: 2,
      type_breakdown: { budget: 1, news: 1 },
      top_signals: [
        {
          signal_id: 10,
          title: "Cloud modernization budget signal",
          signal_type: "budget",
          agency: "DoD",
          relevance_score: 84,
          source_url: null,
          published_at: "2026-02-14T00:00:00",
        },
      ],
      recipient_email: "owner@example.com",
      sent_at: "2026-02-14T10:00:00",
      simulated: true,
    });
  });

  it("runs automation actions and renders digest preview", async () => {
    renderWithQueryClient(<SignalsPage />);

    expect(await screen.findByRole("heading", { name: "Market Signals" })).toBeInTheDocument();
    expect(screen.getByText("Cloud modernization budget signal")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Ingest News" }));
    await waitFor(() => expect(mockedSignalApi.ingestNews).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Analyze Budget Docs" }));
    await waitFor(() => expect(mockedSignalApi.ingestBudgetAnalysis).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Rescore Signals" }));
    await waitFor(() => expect(mockedSignalApi.rescore).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Preview Digest" }));
    await waitFor(() => expect(mockedSignalApi.digestPreview).toHaveBeenCalled());
    expect(await screen.findByTestId("signals-digest-preview-card")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Send Digest" }));
    await waitFor(() => expect(mockedSignalApi.sendDigest).toHaveBeenCalled());
    expect(await screen.findByTestId("signals-action-message")).toHaveTextContent(
      "Digest sent to owner@example.com with 2 signal highlights."
    );
  });
});
