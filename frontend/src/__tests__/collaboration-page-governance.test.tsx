import { fireEvent, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import CollaborationPage from "@/app/(dashboard)/collaboration/page";
import { collaborationApi } from "@/lib/api";
import { renderWithQueryClient } from "@/test/react-query";

vi.mock("next/navigation", () => ({
  useSearchParams: () => ({ get: () => null }),
}));

vi.mock("@/lib/api", () => ({
  collaborationApi: {
    listWorkspaces: vi.fn(),
    createWorkspace: vi.fn(),
    listMembers: vi.fn(),
    listInvitations: vi.fn(),
    listSharedData: vi.fn(),
    listContractFeedCatalog: vi.fn(),
    listContractFeedPresets: vi.fn(),
    applyContractFeedPreset: vi.fn(),
    shareData: vi.fn(),
    unshareData: vi.fn(),
    approveSharedData: vi.fn(),
    getShareGovernanceSummary: vi.fn(),
    getShareGovernanceTrends: vi.fn(),
    getGovernanceAnomalies: vi.fn(),
    getComplianceDigestSchedule: vi.fn(),
    updateComplianceDigestSchedule: vi.fn(),
    getComplianceDigestPreview: vi.fn(),
    getComplianceDigestDeliveries: vi.fn(),
    sendComplianceDigest: vi.fn(),
    exportShareAuditCsv: vi.fn(),
  },
}));

const mockedCollaborationApi = vi.mocked(collaborationApi);

describe("CollaborationPage governance controls", () => {
  it("allows approving pending shared artifacts from the workspace shared-data list", async () => {
    const createObjectUrl = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:mock-audit");
    const revokeObjectUrl = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

    mockedCollaborationApi.listWorkspaces.mockResolvedValue([
      {
        id: 1,
        owner_id: 10,
        name: "Gov Workspace",
        description: "Policy validation workspace",
        member_count: 1,
        created_at: "2026-02-10T12:00:00Z",
        updated_at: "2026-02-10T12:00:00Z",
      },
    ]);
    mockedCollaborationApi.listMembers.mockResolvedValue([
      {
        id: 7,
        workspace_id: 1,
        user_id: 22,
        role: "viewer",
        user_name: "Partner User",
        user_email: "partner@example.com",
        created_at: "2026-02-10T12:00:00Z",
      },
    ]);
    mockedCollaborationApi.listInvitations.mockResolvedValue([]);
    mockedCollaborationApi.listContractFeedCatalog.mockResolvedValue([]);
    mockedCollaborationApi.listContractFeedPresets.mockResolvedValue([]);
    mockedCollaborationApi.getShareGovernanceSummary.mockResolvedValue({
      workspace_id: 1,
      total_shared_items: 1,
      pending_approval_count: 1,
      approved_count: 0,
      revoked_count: 0,
      expired_count: 0,
      expiring_7d_count: 0,
      scoped_share_count: 1,
      global_share_count: 0,
    });
    mockedCollaborationApi.getShareGovernanceTrends.mockResolvedValue({
      workspace_id: 1,
      days: 30,
      sla_hours: 24,
      overdue_pending_count: 0,
      sla_approval_rate: 100,
      points: [
        {
          date: "2026-02-10",
          shared_count: 1,
          approvals_completed_count: 1,
          approved_within_sla_count: 1,
          approved_after_sla_count: 0,
          average_approval_hours: 0.03,
        },
      ],
    });
    mockedCollaborationApi.getGovernanceAnomalies.mockResolvedValue([
      {
        code: "pending_approvals",
        severity: "warning",
        title: "Pending approvals awaiting release",
        description: "Shared artifacts are waiting for governance approval.",
        metric_value: 1,
        threshold: 0,
        recommendation: "Review pending shares and approve/revoke as appropriate.",
      },
    ]);
    mockedCollaborationApi.getComplianceDigestSchedule.mockResolvedValue({
      workspace_id: 1,
      user_id: 10,
      frequency: "weekly",
      day_of_week: 1,
      hour_utc: 13,
      minute_utc: 0,
      channel: "in_app",
      recipient_role: "all",
      anomalies_only: false,
      is_enabled: true,
      last_sent_at: null,
    });
    mockedCollaborationApi.getComplianceDigestPreview
      .mockResolvedValueOnce({
        workspace_id: 1,
        generated_at: "2026-02-10T12:04:00Z",
        recipient_role: "all",
        recipient_count: 2,
        summary: {
          workspace_id: 1,
          total_shared_items: 1,
          pending_approval_count: 1,
          approved_count: 0,
          revoked_count: 0,
          expired_count: 0,
          expiring_7d_count: 0,
          scoped_share_count: 1,
          global_share_count: 0,
        },
        trends: {
          workspace_id: 1,
          days: 30,
          sla_hours: 24,
          overdue_pending_count: 0,
          sla_approval_rate: 100,
          points: [],
        },
        anomalies: [
          {
            code: "pending_approvals",
            severity: "warning",
            title: "Pending approvals awaiting release",
            description: "Shared artifacts are waiting for governance approval.",
            metric_value: 1,
            threshold: 0,
            recommendation: "Review pending shares and approve/revoke as appropriate.",
          },
        ],
        schedule: {
          workspace_id: 1,
          user_id: 10,
          frequency: "weekly",
          day_of_week: 1,
          hour_utc: 13,
          minute_utc: 0,
          channel: "in_app",
          recipient_role: "all",
          anomalies_only: false,
          is_enabled: true,
          last_sent_at: null,
        },
        delivery_summary: {
          total_attempts: 0,
          success_count: 0,
          failed_count: 0,
          retry_attempt_count: 0,
          last_status: null,
          last_failure_reason: null,
          last_sent_at: null,
        },
      })
      .mockResolvedValue({
      workspace_id: 1,
      generated_at: "2026-02-10T12:04:00Z",
      recipient_role: "viewer",
      recipient_count: 1,
      summary: {
        workspace_id: 1,
        total_shared_items: 1,
        pending_approval_count: 1,
        approved_count: 0,
        revoked_count: 0,
        expired_count: 0,
        expiring_7d_count: 0,
        scoped_share_count: 1,
        global_share_count: 0,
      },
      trends: {
        workspace_id: 1,
        days: 30,
        sla_hours: 24,
        overdue_pending_count: 0,
        sla_approval_rate: 100,
        points: [],
      },
      anomalies: [
        {
          code: "pending_approvals",
          severity: "warning",
          title: "Pending approvals awaiting release",
          description: "Shared artifacts are waiting for governance approval.",
          metric_value: 1,
          threshold: 0,
          recommendation: "Review pending shares and approve/revoke as appropriate.",
        },
      ],
      schedule: {
        workspace_id: 1,
        user_id: 10,
        frequency: "weekly",
        day_of_week: 1,
        hour_utc: 13,
        minute_utc: 0,
        channel: "in_app",
        recipient_role: "viewer",
        anomalies_only: false,
        is_enabled: true,
        last_sent_at: null,
      },
      delivery_summary: {
        total_attempts: 1,
        success_count: 1,
        failed_count: 0,
        retry_attempt_count: 0,
        last_status: "success",
        last_failure_reason: null,
        last_sent_at: "2026-02-10T12:04:00Z",
      },
    });
    mockedCollaborationApi.updateComplianceDigestSchedule.mockResolvedValue({
      workspace_id: 1,
      user_id: 10,
      frequency: "weekly",
      day_of_week: 1,
      hour_utc: 13,
      minute_utc: 0,
      channel: "in_app",
      recipient_role: "viewer",
      anomalies_only: false,
      is_enabled: true,
      last_sent_at: null,
    });
    mockedCollaborationApi.sendComplianceDigest.mockResolvedValue({
      workspace_id: 1,
      generated_at: "2026-02-10T12:05:00Z",
      recipient_role: "viewer",
      recipient_count: 1,
      summary: {
        workspace_id: 1,
        total_shared_items: 1,
        pending_approval_count: 1,
        approved_count: 0,
        revoked_count: 0,
        expired_count: 0,
        expiring_7d_count: 0,
        scoped_share_count: 1,
        global_share_count: 0,
      },
      trends: {
        workspace_id: 1,
        days: 30,
        sla_hours: 24,
        overdue_pending_count: 0,
        sla_approval_rate: 100,
        points: [],
      },
      anomalies: [],
      schedule: {
        workspace_id: 1,
        user_id: 10,
        frequency: "weekly",
        day_of_week: 1,
        hour_utc: 13,
        minute_utc: 0,
        channel: "in_app",
        recipient_role: "viewer",
        anomalies_only: false,
        is_enabled: true,
        last_sent_at: "2026-02-10T12:05:00Z",
      },
      delivery_summary: {
        total_attempts: 1,
        success_count: 1,
        failed_count: 0,
        retry_attempt_count: 0,
        last_status: "success",
        last_failure_reason: null,
        last_sent_at: "2026-02-10T12:05:00Z",
      },
    });
    mockedCollaborationApi.getComplianceDigestDeliveries.mockResolvedValue({
      workspace_id: 1,
      user_id: 10,
      summary: {
        total_attempts: 1,
        success_count: 1,
        failed_count: 0,
        retry_attempt_count: 0,
        last_status: "success",
        last_failure_reason: null,
        last_sent_at: "2026-02-10T12:05:00Z",
      },
      items: [
        {
          id: 101,
          workspace_id: 1,
          user_id: 10,
          schedule_id: 9,
          status: "success",
          attempt_number: 1,
          retry_of_delivery_id: null,
          channel: "in_app",
          recipient_role: "viewer",
          recipient_count: 1,
          anomalies_count: 0,
          failure_reason: null,
          generated_at: "2026-02-10T12:05:00Z",
          created_at: "2026-02-10T12:05:00Z",
        },
      ],
    });
    mockedCollaborationApi.exportShareAuditCsv.mockResolvedValue(
      new Blob(["header\nvalue"], { type: "text/csv" })
    );
    mockedCollaborationApi.listSharedData.mockResolvedValue([
      {
        id: 55,
        workspace_id: 1,
        data_type: "rfp_summary",
        entity_id: 9001,
        label: "Entity #9001",
        requires_approval: true,
        approval_status: "pending",
        approved_by_user_id: null,
        approved_at: null,
        expires_at: null,
        partner_user_id: 22,
        created_at: "2026-02-10T12:00:00Z",
      },
    ]);
    mockedCollaborationApi.approveSharedData.mockResolvedValue({
      id: 55,
      workspace_id: 1,
      data_type: "rfp_summary",
      entity_id: 9001,
      label: "Entity #9001",
      requires_approval: true,
      approval_status: "approved",
      approved_by_user_id: 10,
      approved_at: "2026-02-10T12:02:00Z",
      expires_at: null,
      partner_user_id: 22,
      created_at: "2026-02-10T12:00:00Z",
    });

    renderWithQueryClient(<CollaborationPage />);

    await screen.findByRole("heading", { name: "Gov Workspace" });
    fireEvent.click(screen.getByRole("button", { name: /Shared Data \(/ }));
    fireEvent.change(screen.getByLabelText("Digest recipients"), {
      target: { value: "viewer" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save Schedule" }));
    await waitFor(() =>
      expect(mockedCollaborationApi.updateComplianceDigestSchedule).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ recipient_role: "viewer" })
      )
    );
    await waitFor(() =>
      expect(screen.getByTestId("compliance-digest-preview")).toHaveTextContent(
        "recipients: 1 (viewer)"
      )
    );
    expect(screen.getByTestId("compliance-digest-delivery-summary")).toHaveTextContent(
      "Delivery attempts: 1"
    );
    fireEvent.click(await screen.findByTestId("export-governance-audit"));
    await waitFor(() =>
      expect(mockedCollaborationApi.exportShareAuditCsv).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          days: 30,
        })
      )
    );
    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));

    await waitFor(() =>
      expect(mockedCollaborationApi.approveSharedData).toHaveBeenCalledWith(1, 55)
    );
    expect(screen.getByTestId("governance-sla-percent")).toHaveTextContent("100%");

    createObjectUrl.mockRestore();
    revokeObjectUrl.mockRestore();
  });

  it("opens MFA modal for audit export step-up and retries with entered code", async () => {
    vi.clearAllMocks();

    const createObjectUrl = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:mock-audit");
    const revokeObjectUrl = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

    mockedCollaborationApi.listWorkspaces.mockResolvedValue([
      {
        id: 1,
        owner_id: 10,
        name: "Gov Workspace",
        description: "Policy validation workspace",
        member_count: 1,
        created_at: "2026-02-10T12:00:00Z",
        updated_at: "2026-02-10T12:00:00Z",
      },
    ]);
    mockedCollaborationApi.listMembers.mockResolvedValue([]);
    mockedCollaborationApi.listInvitations.mockResolvedValue([]);
    mockedCollaborationApi.listSharedData.mockResolvedValue([]);
    mockedCollaborationApi.listContractFeedCatalog.mockResolvedValue([]);
    mockedCollaborationApi.listContractFeedPresets.mockResolvedValue([]);
    mockedCollaborationApi.getShareGovernanceSummary.mockResolvedValue({
      workspace_id: 1,
      total_shared_items: 0,
      pending_approval_count: 0,
      approved_count: 0,
      revoked_count: 0,
      expired_count: 0,
      expiring_7d_count: 0,
      scoped_share_count: 0,
      global_share_count: 0,
    });
    mockedCollaborationApi.getShareGovernanceTrends.mockResolvedValue({
      workspace_id: 1,
      days: 30,
      sla_hours: 24,
      overdue_pending_count: 0,
      sla_approval_rate: 100,
      points: [],
    });
    mockedCollaborationApi.getGovernanceAnomalies.mockResolvedValue([]);
    mockedCollaborationApi.getComplianceDigestSchedule.mockResolvedValue({
      workspace_id: 1,
      user_id: 10,
      frequency: "weekly",
      day_of_week: 1,
      hour_utc: 13,
      minute_utc: 0,
      channel: "in_app",
      recipient_role: "all",
      anomalies_only: false,
      is_enabled: true,
      last_sent_at: null,
    });
    mockedCollaborationApi.getComplianceDigestPreview.mockResolvedValue({
      workspace_id: 1,
      generated_at: "2026-02-10T12:04:00Z",
      recipient_role: "all",
      recipient_count: 0,
      summary: {
        workspace_id: 1,
        total_shared_items: 0,
        pending_approval_count: 0,
        approved_count: 0,
        revoked_count: 0,
        expired_count: 0,
        expiring_7d_count: 0,
        scoped_share_count: 0,
        global_share_count: 0,
      },
      trends: {
        workspace_id: 1,
        days: 30,
        sla_hours: 24,
        overdue_pending_count: 0,
        sla_approval_rate: 100,
        points: [],
      },
      anomalies: [],
      schedule: {
        workspace_id: 1,
        user_id: 10,
        frequency: "weekly",
        day_of_week: 1,
        hour_utc: 13,
        minute_utc: 0,
        channel: "in_app",
        recipient_role: "all",
        anomalies_only: false,
        is_enabled: true,
        last_sent_at: null,
      },
      delivery_summary: {
        total_attempts: 0,
        success_count: 0,
        failed_count: 0,
        retry_attempt_count: 0,
        last_status: null,
        last_failure_reason: null,
        last_sent_at: null,
      },
    });
    mockedCollaborationApi.getComplianceDigestDeliveries.mockResolvedValue({
      workspace_id: 1,
      user_id: 10,
      summary: {
        total_attempts: 0,
        success_count: 0,
        failed_count: 0,
        retry_attempt_count: 0,
        last_status: null,
        last_failure_reason: null,
        last_sent_at: null,
      },
      items: [],
    });
    mockedCollaborationApi.exportShareAuditCsv
      .mockRejectedValueOnce({
        response: { headers: { "x-step-up-required": "true" } },
      })
      .mockResolvedValueOnce(new Blob(["header\nvalue"], { type: "text/csv" }));

    renderWithQueryClient(<CollaborationPage />);

    await screen.findByRole("heading", { name: "Gov Workspace" });
    fireEvent.click(screen.getByRole("button", { name: /Shared Data \(/ }));

    expect(screen.queryByLabelText("Step-up code")).not.toBeInTheDocument();

    fireEvent.click(await screen.findByTestId("export-governance-audit"));

    expect(
      await screen.findByText("Step-Up Required for Audit Export")
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Step-up authentication code"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() =>
      expect(mockedCollaborationApi.exportShareAuditCsv).toHaveBeenNthCalledWith(
        2,
        1,
        expect.objectContaining({
          days: 30,
          step_up_code: "123456",
        })
      )
    );

    createObjectUrl.mockRestore();
    revokeObjectUrl.mockRestore();
  });
});
