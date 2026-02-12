import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import HelpCenterPage from "@/app/(dashboard)/help/page";
import { supportApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  supportApi: {
    listArticles: vi.fn(),
    listTutorials: vi.fn(),
    chat: vi.fn(),
  },
}));

const mockedSupportApi = vi.mocked(supportApi);

describe("Help center page", () => {
  beforeEach(() => {
    mockedSupportApi.listArticles.mockResolvedValue([
      {
        id: "report-builder-guide",
        title: "Report Builder and Delivery Guide",
        category: "Reporting",
        summary: "Build and schedule reports.",
        content: "Use the report builder and email scheduling controls.",
        tags: ["reports"],
        last_updated: "2026-02-10",
      },
    ]);
    mockedSupportApi.listTutorials.mockResolvedValue([
      {
        id: "tutorial-reports",
        title: "Custom Reports Walkthrough",
        feature: "Reporting",
        estimated_minutes: 7,
        steps: [
          {
            title: "Build a Field Layout",
            instruction: "Drag fields into the selected list.",
            route: "/reports",
            action_label: "Open Reports",
          },
        ],
      },
    ]);
    mockedSupportApi.chat.mockResolvedValue({
      reply: "Use Reports to build and share views.",
      suggested_article_ids: ["report-builder-guide"],
      suggested_tutorial_id: "tutorial-reports",
      generated_at: "2026-02-10T12:00:00Z",
    });
  });

  it("renders help resources and support chat response", async () => {
    render(<HelpCenterPage />);

    expect((await screen.findAllByText("Report Builder and Delivery Guide")).length).toBeGreaterThan(
      0
    );
    expect((await screen.findAllByText("Custom Reports Walkthrough")).length).toBeGreaterThan(0);

    fireEvent.change(
      screen.getByPlaceholderText(
        "Ask support anything about onboarding, templates, or reports..."
      ),
      { target: { value: "How do I schedule reports?" } }
    );
    fireEvent.click(screen.getByRole("button", { name: "Ask Support" }));

    await waitFor(() =>
      expect(screen.getByText("Use Reports to build and share views.")).toBeInTheDocument()
    );
  });
});
