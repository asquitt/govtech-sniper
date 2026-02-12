import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import IntegrationsPage from "@/app/(dashboard)/settings/integrations/page";
import { enterpriseApi, sharepointApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  enterpriseApi: {
    listWebhooks: vi.fn(),
    listSecrets: vi.fn(),
    createWebhook: vi.fn(),
    updateWebhook: vi.fn(),
    deleteWebhook: vi.fn(),
    listWebhookDeliveries: vi.fn(),
    createOrUpdateSecret: vi.fn(),
    deleteSecret: vi.fn(),
  },
  sharepointApi: {
    status: vi.fn(),
    browse: vi.fn(),
    download: vi.fn(),
  },
}));

const mockedEnterpriseApi = vi.mocked(enterpriseApi);
const mockedSharePointApi = vi.mocked(sharepointApi);

describe("Settings Integrations Page", () => {
  beforeEach(() => {
    mockedEnterpriseApi.listWebhooks.mockResolvedValue([
      {
        id: 10,
        name: "Ops Hook",
        target_url: "https://example.com/hooks/ops",
        secret: null,
        event_types: ["rfp.created"],
        is_active: true,
        created_at: "2026-02-10T12:00:00Z",
        updated_at: "2026-02-10T12:00:00Z",
      },
    ]);
    mockedEnterpriseApi.listSecrets.mockResolvedValue([
      {
        id: 20,
        key: "SCIM_BEARER_TOKEN",
        value: "********",
        created_at: "2026-02-10T12:00:00Z",
        updated_at: "2026-02-10T12:00:00Z",
      },
    ]);
    mockedSharePointApi.status.mockResolvedValue({
      configured: false,
      enabled: false,
      connected: false,
    });
    mockedSharePointApi.browse.mockResolvedValue([]);
  });

  it("renders SharePoint, webhook, and secrets controls", async () => {
    render(<IntegrationsPage />);

    expect(await screen.findByText("SharePoint Browser")).toBeInTheDocument();
    expect(await screen.findByText("Webhook Subscriptions")).toBeInTheDocument();
    expect(await screen.findByText("Ops Hook")).toBeInTheDocument();
    expect(await screen.findByText("Secrets Vault")).toBeInTheDocument();
    expect(await screen.findByText("SCIM_BEARER_TOKEN")).toBeInTheDocument();
  });
});
