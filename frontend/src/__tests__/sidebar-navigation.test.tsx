import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { Sidebar } from "@/components/layout/sidebar";

vi.mock("next/navigation", () => ({
  usePathname: () => "/opportunities",
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: "test@example.com",
      full_name: "Test User",
      tier: "professional",
    },
    logout: vi.fn(),
  }),
}));

vi.mock("@/components/onboarding/onboarding-wizard", () => ({
  OnboardingWizard: () => <div>Onboarding Mock</div>,
}));

describe("Sidebar", () => {
  it("shows integrated templates and word add-in links", async () => {
    render(<Sidebar collapsed={false} onToggle={vi.fn()} />);

    expect(await screen.findByRole("link", { name: "Templates" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Word Add-in" })).toBeInTheDocument();
  });
});
