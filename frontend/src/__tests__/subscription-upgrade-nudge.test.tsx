import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SubscriptionPage from "@/app/(dashboard)/settings/subscription/page";
import { subscriptionApi } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: () => null,
  }),
}));

vi.mock("@/lib/api", () => ({
  subscriptionApi: {
    listPlans: vi.fn(),
    currentPlan: vi.fn(),
    usage: vi.fn(),
    status: vi.fn(),
    checkout: vi.fn(),
    portal: vi.fn(),
  },
}));

const mockedSubscriptionApi = vi.mocked(subscriptionApi);

describe("Subscription Upgrade Nudge", () => {
  it("shows an upgrade nudge when usage is near limits", async () => {
    mockedSubscriptionApi.listPlans.mockResolvedValue([
      {
        tier: "free",
        label: "Free",
        price_monthly: 0,
        price_yearly: 0,
        description: "Free",
        features: [],
        limits: { rfps: 10, proposals: 5, api_calls_per_day: 100 },
      },
      {
        tier: "starter",
        label: "Starter",
        price_monthly: 9900,
        price_yearly: 95000,
        description: "Starter",
        features: [],
        limits: { rfps: 50, proposals: 20, api_calls_per_day: 500 },
      },
    ]);
    mockedSubscriptionApi.currentPlan.mockResolvedValue({
      tier: "free",
      label: "Free",
      price_monthly: 0,
      price_yearly: 0,
      description: "Free",
      features: [],
      limits: { rfps: 10, proposals: 5, api_calls_per_day: 100 },
    });
    mockedSubscriptionApi.usage.mockResolvedValue({
      rfps_used: 8,
      rfps_limit: 10,
      proposals_used: 2,
      proposals_limit: 5,
      api_calls_used: 12,
      api_calls_limit: 100,
    });
    mockedSubscriptionApi.status.mockResolvedValue({
      tier: "free",
      status: "free",
      expires_at: null,
      has_stripe_customer: false,
      has_subscription: false,
    });

    render(<SubscriptionPage />);

    expect(
      await screen.findByText(/RFP tracking quota is nearing its limit/i)
    ).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Upgrade" })).toBeInTheDocument();
  });
});
