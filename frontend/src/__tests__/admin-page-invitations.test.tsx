import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { vi } from "vitest";
import AdminPage from "@/app/(dashboard)/admin/page";
import { adminApi } from "@/lib/api";

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({ user: { id: 1 } }),
}));

vi.mock("@/lib/api", () => ({
  adminApi: {
    getOrganization: vi.fn(),
    listMembers: vi.fn(),
    listMemberInvitations: vi.fn(),
    inviteMember: vi.fn(),
    activateMemberInvitation: vi.fn(),
    revokeMemberInvitation: vi.fn(),
    resendMemberInvitation: vi.fn(),
    updateMemberRole: vi.fn(),
    deactivateMember: vi.fn(),
    reactivateMember: vi.fn(),
    getUsageAnalytics: vi.fn(),
    getAuditLog: vi.fn(),
    getCapabilityHealth: vi.fn(),
  },
}));

const mockedAdminApi = vi.mocked(adminApi);

describe("AdminPage invitation flow", () => {
  it("invites and activates members from org-admin UI", async () => {
    mockedAdminApi.getOrganization.mockResolvedValue({
      id: 9,
      name: "Test Org",
      slug: "test-org",
      domain: null,
      billing_email: null,
      sso_enabled: false,
      sso_provider: null,
      sso_enforce: false,
      sso_auto_provision: false,
      logo_url: null,
      primary_color: null,
      ip_allowlist: [],
      data_retention_days: 365,
      require_step_up_for_sensitive_exports: true,
      require_step_up_for_sensitive_shares: true,
      member_count: 1,
      created_at: "2026-02-10T12:00:00Z",
    });
    mockedAdminApi.listMembers.mockResolvedValue({ members: [], total: 0 });
    mockedAdminApi.listMemberInvitations.mockResolvedValue([
      {
        id: 41,
        email: "invitee@example.com",
        role: "member",
        status: "pending",
        expires_at: "2026-02-20T12:00:00Z",
        activated_at: null,
        accepted_user_id: null,
        invited_by_user_id: 1,
        activation_ready: true,
        invite_age_hours: 24,
        invite_age_days: 1,
        days_until_expiry: 10,
        sla_state: "healthy",
      },
      {
        id: 43,
        email: "pending@example.com",
        role: "viewer",
        status: "pending",
        expires_at: "2026-02-19T12:00:00Z",
        activated_at: null,
        accepted_user_id: null,
        invited_by_user_id: 1,
        activation_ready: false,
        invite_age_hours: 46,
        invite_age_days: 2,
        days_until_expiry: 9,
        sla_state: "expiring",
      },
    ]);
    mockedAdminApi.getUsageAnalytics.mockResolvedValue({
      members: 1,
      proposals: 0,
      rfps: 0,
      audit_events: 0,
      active_users: 1,
      by_action: [],
      period_days: 30,
    });
    mockedAdminApi.getAuditLog.mockResolvedValue({ events: [], total: 0 });
    mockedAdminApi.getCapabilityHealth.mockResolvedValue({
      organization_id: 9,
      timestamp: "2026-02-10T12:00:00Z",
      runtime: {
        debug: true,
        mock_ai: true,
        mock_sam_gov: true,
        database_engine: "sqlite",
        websocket: {
          endpoint: "/api/v1/ws",
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
      integrations_by_provider: [],
      discoverability: [],
    });
    mockedAdminApi.inviteMember.mockResolvedValue({
      id: 42,
      email: "new-user@example.com",
      role: "member",
      status: "pending",
      expires_at: "2026-02-18T12:00:00Z",
      activated_at: null,
      accepted_user_id: null,
      invited_by_user_id: 1,
      activation_ready: false,
      invite_age_hours: 0,
      invite_age_days: 0,
      days_until_expiry: 8,
      sla_state: "healthy",
    });
    mockedAdminApi.activateMemberInvitation.mockResolvedValue({
      id: 41,
      email: "invitee@example.com",
      role: "member",
      status: "activated",
      expires_at: "2026-02-20T12:00:00Z",
      activated_at: "2026-02-10T12:15:00Z",
      accepted_user_id: 99,
      invited_by_user_id: 1,
      activation_ready: true,
      invite_age_hours: 25,
      invite_age_days: 1,
      days_until_expiry: 9,
      sla_state: "completed",
    });
    mockedAdminApi.resendMemberInvitation.mockResolvedValue({
      id: 43,
      email: "pending@example.com",
      role: "viewer",
      status: "pending",
      expires_at: "2026-02-24T12:00:00Z",
      activated_at: null,
      accepted_user_id: null,
      invited_by_user_id: 1,
      activation_ready: false,
      invite_age_hours: 0,
      invite_age_days: 0,
      days_until_expiry: 14,
      sla_state: "healthy",
    });
    mockedAdminApi.revokeMemberInvitation.mockResolvedValue({
      id: 43,
      email: "pending@example.com",
      role: "viewer",
      status: "revoked",
      expires_at: "2026-02-24T12:00:00Z",
      activated_at: null,
      accepted_user_id: null,
      invited_by_user_id: 1,
      activation_ready: false,
      invite_age_hours: 1,
      invite_age_days: 0,
      days_until_expiry: 13,
      sla_state: "revoked",
    });

    render(<AdminPage />);
    await screen.findByText("Member Invitations");

    fireEvent.change(screen.getByLabelText("Invite member email"), {
      target: { value: "new-user@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Invite" }));
    await waitFor(() =>
      expect(mockedAdminApi.inviteMember).toHaveBeenCalledWith({
        email: "new-user@example.com",
        role: "member",
        expires_in_days: 7,
      })
    );

    const pendingRow = await screen.findByTestId("org-invitation-43");
    fireEvent.click(within(pendingRow).getByRole("button", { name: "Resend" }));
    await waitFor(() =>
      expect(mockedAdminApi.resendMemberInvitation).toHaveBeenCalledWith(43, 7)
    );

    const refreshedPendingRow = await screen.findByTestId("org-invitation-43");
    fireEvent.click(within(refreshedPendingRow).getByRole("button", { name: "Revoke" }));
    await waitFor(() =>
      expect(mockedAdminApi.revokeMemberInvitation).toHaveBeenCalledWith(43)
    );

    const readyRow = await screen.findByTestId("org-invitation-41");
    fireEvent.click(within(readyRow).getByRole("button", { name: "Activate" }));
    await waitFor(() =>
      expect(mockedAdminApi.activateMemberInvitation).toHaveBeenCalledWith(41)
    );
  });
});
