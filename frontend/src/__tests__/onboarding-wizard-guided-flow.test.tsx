import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import api from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockedApi = vi.mocked(api);

describe("Onboarding guided setup wizard", () => {
  beforeEach(() => {
    mockedApi.get.mockResolvedValue({
      data: {
        steps: [
          {
            id: "create_account",
            title: "Create your account",
            description: "Profile setup",
            href: "/settings",
            completed: true,
            completed_at: "2026-02-10T00:00:00Z",
          },
          {
            id: "upload_rfp",
            title: "Upload your first RFP",
            description: "Add solicitation",
            href: "/opportunities",
            completed: false,
            completed_at: null,
          },
        ],
        completed_count: 1,
        total_steps: 2,
        is_complete: false,
        is_dismissed: false,
      },
    });
    mockedApi.post.mockResolvedValue({ data: { status: "completed" } });
  });

  it("opens guided setup modal and marks current step complete", async () => {
    render(<OnboardingWizard />);

    fireEvent.click(await screen.findByRole("button", { name: "Guided Setup" }));
    expect(await screen.findByText("Guided Setup Wizard")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Mark Complete" }));

    await waitFor(() =>
      expect(mockedApi.post).toHaveBeenCalledWith("/onboarding/steps/upload_rfp/complete")
    );
  });
});
