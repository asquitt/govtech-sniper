import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import EventsPage from "@/app/(dashboard)/events/page";
import { eventApi } from "@/lib/api";

vi.mock("@/components/layout/header", () => ({
  Header: ({ title, actions }: { title: string; actions?: unknown }) => (
    <div>
      <h1>{title}</h1>
      {actions as JSX.Element | null}
    </div>
  ),
}));

vi.mock("@/lib/api", () => ({
  eventApi: {
    list: vi.fn(),
    upcoming: vi.fn(),
    calendar: vi.fn(),
    ingest: vi.fn(),
    alerts: vi.fn(),
    create: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockedEventApi = vi.mocked(eventApi);

describe("EventsPage", () => {
  beforeEach(() => {
    mockedEventApi.list.mockResolvedValue([
      {
        id: 1,
        user_id: 1,
        title: "Industry Day",
        agency: "DHS",
        event_type: "industry_day",
        date: "2026-03-01T14:00:00",
        location: "Washington, DC",
        registration_url: null,
        related_rfp_id: null,
        description: "Overview session.",
        source: "sam.gov",
        is_archived: false,
        created_at: "2026-02-01T00:00:00",
        updated_at: "2026-02-01T00:00:00",
      },
    ]);
    mockedEventApi.upcoming.mockResolvedValue([
      {
        id: 1,
        user_id: 1,
        title: "Industry Day",
        agency: "DHS",
        event_type: "industry_day",
        date: "2026-03-01T14:00:00",
        location: "Washington, DC",
        registration_url: null,
        related_rfp_id: null,
        description: "Overview session.",
        source: "sam.gov",
        is_archived: false,
        created_at: "2026-02-01T00:00:00",
        updated_at: "2026-02-01T00:00:00",
      },
    ]);
    mockedEventApi.alerts.mockResolvedValue({
      alerts: [
        {
          event: {
            id: 1,
            user_id: 1,
            title: "Industry Day",
            agency: "DHS",
            event_type: "industry_day",
            date: "2026-03-01T14:00:00",
            location: "Washington, DC",
            registration_url: null,
            related_rfp_id: null,
            description: "Overview session.",
            source: "sam.gov",
            is_archived: false,
            created_at: "2026-02-01T00:00:00",
            updated_at: "2026-02-01T00:00:00",
          },
          relevance_score: 90,
          match_reasons: ["Agency alignment (DHS)"],
          days_until_event: 8,
        },
      ],
      total: 1,
      evaluated: 1,
    });
    mockedEventApi.calendar.mockResolvedValue([
      {
        id: 1,
        user_id: 1,
        title: "Industry Day",
        agency: "DHS",
        event_type: "industry_day",
        date: "2026-03-01T14:00:00",
        location: "Washington, DC",
        registration_url: null,
        related_rfp_id: null,
        description: "Overview session.",
        source: "sam.gov",
        is_archived: false,
        created_at: "2026-02-01T00:00:00",
        updated_at: "2026-02-01T00:00:00",
      },
    ]);
    mockedEventApi.ingest.mockResolvedValue({
      created: 2,
      existing: 1,
      candidates: 3,
      created_event_ids: [2, 3],
      source_breakdown: { "rfp:sam.gov": 1, "curated:dhs-business-opportunities": 1 },
    });
  });

  it("renders alerts and calendar view", async () => {
    render(<EventsPage />);

    expect(await screen.findByRole("heading", { name: "Industry Days & Events" })).toBeInTheDocument();
    expect(await screen.findByText("Relevant Event Alerts")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Calendar" }));
    expect(await screen.findByTestId("events-calendar-grid")).toBeInTheDocument();
  });

  it("ingests events from sources and shows summary", async () => {
    render(<EventsPage />);
    await screen.findByRole("heading", { name: "Industry Days & Events" });

    fireEvent.click(screen.getByRole("button", { name: "Ingest from Sources" }));

    await waitFor(() =>
      expect(mockedEventApi.ingest).toHaveBeenCalledWith({
        days_ahead: 120,
        include_curated: true,
      })
    );
    expect(await screen.findByTestId("events-ingest-summary")).toHaveTextContent(
      "Ingestion completed: 2 new events, 1 already tracked."
    );
  });
});
