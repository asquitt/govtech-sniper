import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import ReportsPage from "@/app/(dashboard)/reports/page";
import { reportApi } from "@/lib/api/reports";

vi.mock("@/lib/api/reports", () => ({
  reportApi: {
    list: vi.fn(),
    create: vi.fn(),
    get: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    generate: vi.fn(),
    export: vi.fn(),
    setSchedule: vi.fn(),
    share: vi.fn(),
    getDelivery: vi.fn(),
    sendDeliveryNow: vi.fn(),
  },
}));

const mockedReportApi = vi.mocked(reportApi);

describe("Reports page builder", () => {
  beforeEach(() => {
    mockedReportApi.list.mockResolvedValue([]);
    mockedReportApi.create.mockResolvedValue({
      id: 1,
      user_id: 1,
      name: "Pipeline Builder",
      report_type: "pipeline",
      config: {
        columns: ["opportunity", "agency", "value"],
        filters: {},
        group_by: null,
        sort_by: null,
        sort_order: "asc",
      },
      schedule: "weekly",
      is_shared: false,
      shared_with_emails: [],
      delivery_recipients: [],
      delivery_enabled: false,
      delivery_subject: null,
      last_generated_at: null,
      last_delivered_at: null,
      created_at: "2026-02-10T00:00:00Z",
      updated_at: "2026-02-10T00:00:00Z",
    });
  });

  it("creates report with drag-and-drop field builder config", async () => {
    render(<ReportsPage />);

    fireEvent.click(await screen.findByRole("button", { name: "New Report" }));
    expect(await screen.findByText("Available Fields (drag to selected)")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("e.g. Monthly Pipeline Summary"), {
      target: { value: "Pipeline Builder" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => expect(mockedReportApi.create).toHaveBeenCalled());
    const payload = mockedReportApi.create.mock.calls[0][0];
    expect(payload.config?.columns.length).toBeGreaterThan(0);
    expect(payload.schedule).toBe("weekly");
  });
});
