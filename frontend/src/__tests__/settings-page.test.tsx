import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import SettingsPage from "@/app/(dashboard)/settings/page";
import { analyticsApi, auditApi, integrationApi, teamApi } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  integrationApi: {
    list: vi.fn(),
    create: vi.fn(),
    providers: vi.fn(),
    test: vi.fn(),
    authorizeSso: vi.fn(),
    sync: vi.fn(),
    syncs: vi.fn(),
    sendWebhook: vi.fn(),
    listWebhooks: vi.fn(),
    update: vi.fn(),
  },
  teamApi: {
    list: vi.fn(),
    get: vi.fn(),
    updateMemberRole: vi.fn(),
  },
  analyticsApi: {
    getObservability: vi.fn(),
  },
  auditApi: {
    summary: vi.fn(),
    list: vi.fn(),
  },
}));

const mockedIntegrationApi = vi.mocked(integrationApi);
const mockedTeamApi = vi.mocked(teamApi);
const mockedAnalyticsApi = vi.mocked(analyticsApi);
const mockedAuditApi = vi.mocked(auditApi);

describe("SettingsPage", () => {
  beforeEach(() => {
    mockedIntegrationApi.list.mockResolvedValue([]);
    mockedIntegrationApi.providers.mockResolvedValue([]);
    mockedTeamApi.list.mockResolvedValue([]);
    mockedAnalyticsApi.getObservability.mockResolvedValue({
      period_days: 30,
      audit_events: { total: 0 },
      integration_syncs: {
        total: 0,
        success: 0,
        failed: 0,
        last_sync_at: null,
        by_provider: {},
      },
      webhook_events: { total: 0, by_provider: {} },
    });
    mockedAuditApi.summary.mockResolvedValue({
      period_days: 30,
      total_events: 0,
      by_action: [],
      by_entity_type: [],
    });
    mockedAuditApi.list.mockResolvedValue([]);
  });

  it("renders settings header", async () => {
    render(<SettingsPage />);
    expect(
      await screen.findByText("Manage integrations and admin configuration")
    ).toBeInTheDocument();
    expect(await screen.findByText("Audit & Observability")).toBeInTheDocument();
    expect(await screen.findByText("Team Roles")).toBeInTheDocument();
  });
});
