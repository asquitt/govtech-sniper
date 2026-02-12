import { render, screen } from "@testing-library/react";
import { CapabilityHealthCard } from "@/app/(dashboard)/admin/_components/CapabilityHealthCard";
import type { AdminCapabilityHealth } from "@/types";

const sampleCapabilityHealth: AdminCapabilityHealth = {
  organization_id: 42,
  timestamp: "2026-02-09T12:00:00Z",
  runtime: {
    debug: true,
    mock_ai: true,
    mock_sam_gov: true,
    database_engine: "sqlite",
    websocket: {
      endpoint: "/api/v1/ws?token=<jwt>",
      active_connections: 0,
      watched_tasks: 0,
      active_documents: 0,
      presence_users: 0,
      active_section_locks: 0,
      active_cursors: 0,
    },
  },
  workers: {
    broker_reachable: false,
    worker_online: false,
    task_mode: "sync_fallback",
  },
  enterprise: {
    scim_configured: false,
    scim_default_team_name: "Default Team",
    webhook_subscriptions: 0,
    stored_secrets: 0,
  },
  integrations_by_provider: [
    { provider: "sharepoint", total: 2, enabled: 1 },
    { provider: "word_addin", total: 1, enabled: 1 },
  ],
  discoverability: [
    {
      capability: "Template Marketplace",
      frontend_path: "/templates",
      backend_prefix: "/api/v1/templates",
      status: "integrated",
      note: "Primary dashboard navigation route enabled.",
    },
    {
      capability: "SCIM Provisioning",
      frontend_path: null,
      backend_prefix: "/api/v1/scim/v2",
      status: "needs_configuration",
      note: "Set SCIM_BEARER_TOKEN to enable SCIM provisioning.",
    },
  ],
};

describe("CapabilityHealthCard", () => {
  it("renders task mode and discoverability links", async () => {
    render(
      <CapabilityHealthCard
        capabilityHealth={sampleCapabilityHealth}
        loading={false}
      />
    );

    expect(await screen.findByText("Capability Health")).toBeInTheDocument();
    expect(await screen.findByText("Sync fallback")).toBeInTheDocument();
    expect(await screen.findByText("Template Marketplace")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "/templates" })).toBeInTheDocument();
    expect(await screen.findByText("SCIM Provisioning")).toBeInTheDocument();
    expect(await screen.findByText("Backend only")).toBeInTheDocument();
  });
});
