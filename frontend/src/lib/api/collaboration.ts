import api from "./client";
import type {
  SharedWorkspace,
  WorkspaceInvitation,
  WorkspaceMember,
  SharedDataPermission,
  PortalView,
  SharedDataType,
  ContractFeedCatalogItem,
  ContractFeedPresetItem,
  ComplianceDigestDeliveryList,
  ComplianceDigestPreview,
  ComplianceDigestSchedule,
  GovernanceAnomaly,
  ShareGovernanceSummary,
  ShareGovernanceTrends,
  SharePresetApplyResponse,
  DocumentPresence,
  SectionLock,
  InboxMessage,
  InboxListResponse,
  InboxMessageType,
} from "@/types";

export const collaborationApi = {
  // Workspaces
  listWorkspaces: async (): Promise<SharedWorkspace[]> => {
    const { data } = await api.get("/collaboration/workspaces");
    return data;
  },

  createWorkspace: async (payload: {
    name: string;
    rfp_id?: number | null;
    description?: string | null;
  }): Promise<SharedWorkspace> => {
    const { data } = await api.post("/collaboration/workspaces", payload);
    return data;
  },

  updateWorkspace: async (
    workspaceId: number,
    payload: { name?: string; description?: string }
  ): Promise<SharedWorkspace> => {
    const { data } = await api.patch(
      `/collaboration/workspaces/${workspaceId}`,
      payload
    );
    return data;
  },

  deleteWorkspace: async (workspaceId: number): Promise<void> => {
    await api.delete(`/collaboration/workspaces/${workspaceId}`);
  },

  // Invitations
  invite: async (
    workspaceId: number,
    payload: { email: string; role?: string }
  ): Promise<WorkspaceInvitation> => {
    const { data } = await api.post(
      `/collaboration/workspaces/${workspaceId}/invite`,
      payload
    );
    return data;
  },

  listInvitations: async (
    workspaceId: number
  ): Promise<WorkspaceInvitation[]> => {
    const { data } = await api.get(
      `/collaboration/workspaces/${workspaceId}/invitations`
    );
    return data;
  },

  acceptInvitation: async (token: string): Promise<WorkspaceMember> => {
    const { data } = await api.post(
      `/collaboration/invitations/accept?token=${encodeURIComponent(token)}`
    );
    return data;
  },

  // Members
  listMembers: async (workspaceId: number): Promise<WorkspaceMember[]> => {
    const { data } = await api.get(
      `/collaboration/workspaces/${workspaceId}/members`
    );
    return data;
  },

  removeMember: async (
    workspaceId: number,
    memberId: number
  ): Promise<void> => {
    await api.delete(
      `/collaboration/workspaces/${workspaceId}/members/${memberId}`
    );
  },

  updateMemberRole: async (
    workspaceId: number,
    memberId: number,
    role: string
  ): Promise<WorkspaceMember> => {
    const { data } = await api.patch(
      `/collaboration/workspaces/${workspaceId}/members/${memberId}/role`,
      { role }
    );
    return data;
  },

  // Data sharing
  listContractFeedCatalog: async (): Promise<ContractFeedCatalogItem[]> => {
    const { data } = await api.get("/collaboration/contract-feeds/catalog");
    return data;
  },

  listContractFeedPresets: async (): Promise<ContractFeedPresetItem[]> => {
    const { data } = await api.get("/collaboration/contract-feeds/presets");
    return data;
  },

  applyContractFeedPreset: async (
    workspaceId: number,
    presetKey: string,
    stepUpCode?: string
  ): Promise<SharePresetApplyResponse> => {
    const { data } = await api.post(
      `/collaboration/workspaces/${workspaceId}/share/preset`,
      { preset_key: presetKey, step_up_code: stepUpCode }
    );
    return data;
  },

  shareData: async (
    workspaceId: number,
    payload: {
      data_type: SharedDataType;
      entity_id: number;
      requires_approval?: boolean;
      expires_at?: string | null;
      partner_user_id?: number | null;
      step_up_code?: string | null;
    }
  ): Promise<SharedDataPermission> => {
    const { data } = await api.post(
      `/collaboration/workspaces/${workspaceId}/share`,
      payload
    );
    return data;
  },

  approveSharedData: async (
    workspaceId: number,
    permId: number
  ): Promise<SharedDataPermission> => {
    const { data } = await api.post(
      `/collaboration/workspaces/${workspaceId}/shared/${permId}/approve`
    );
    return data;
  },

  listSharedData: async (
    workspaceId: number
  ): Promise<SharedDataPermission[]> => {
    const { data } = await api.get(
      `/collaboration/workspaces/${workspaceId}/shared`
    );
    return data;
  },

  getShareGovernanceSummary: async (
    workspaceId: number
  ): Promise<ShareGovernanceSummary> => {
    const { data } = await api.get(
      `/collaboration/workspaces/${workspaceId}/shared/governance-summary`
    );
    return data;
  },

  getShareGovernanceTrends: async (
    workspaceId: number,
    params?: { days?: number; sla_hours?: number }
  ): Promise<ShareGovernanceTrends> => {
    const { data } = await api.get(
      `/collaboration/workspaces/${workspaceId}/shared/governance-trends`,
      { params }
    );
    return data;
  },

  getGovernanceAnomalies: async (
    workspaceId: number,
    params?: { days?: number; sla_hours?: number }
  ): Promise<GovernanceAnomaly[]> => {
    const { data } = await api.get(
      `/collaboration/workspaces/${workspaceId}/shared/governance-anomalies`,
      { params }
    );
    return data;
  },

  getComplianceDigestSchedule: async (
    workspaceId: number
  ): Promise<ComplianceDigestSchedule> => {
    const { data } = await api.get(
      `/collaboration/workspaces/${workspaceId}/compliance-digest-schedule`
    );
    return data;
  },

  updateComplianceDigestSchedule: async (
    workspaceId: number,
    payload: Partial<{
      frequency: "daily" | "weekly";
      day_of_week: number | null;
      hour_utc: number;
      minute_utc: number;
      channel: "in_app" | "email";
      recipient_role: "all" | "owner" | "admin" | "contributor" | "viewer";
      anomalies_only: boolean;
      is_enabled: boolean;
    }>
  ): Promise<ComplianceDigestSchedule> => {
    const { data } = await api.patch(
      `/collaboration/workspaces/${workspaceId}/compliance-digest-schedule`,
      payload
    );
    return data;
  },

  getComplianceDigestPreview: async (
    workspaceId: number,
    params?: { days?: number; sla_hours?: number }
  ): Promise<ComplianceDigestPreview> => {
    const { data } = await api.get(
      `/collaboration/workspaces/${workspaceId}/compliance-digest-preview`,
      { params }
    );
    return data;
  },

  sendComplianceDigest: async (
    workspaceId: number,
    params?: { days?: number; sla_hours?: number }
  ): Promise<ComplianceDigestPreview> => {
    const { data } = await api.post(
      `/collaboration/workspaces/${workspaceId}/compliance-digest-send`,
      null,
      { params }
    );
    return data;
  },

  getComplianceDigestDeliveries: async (
    workspaceId: number,
    params?: { limit?: number }
  ): Promise<ComplianceDigestDeliveryList> => {
    const { data } = await api.get(
      `/collaboration/workspaces/${workspaceId}/compliance-digest-deliveries`,
      { params }
    );
    return data;
  },

  exportShareAuditCsv: async (
    workspaceId: number,
    params?: { days?: number; step_up_code?: string }
  ): Promise<Blob> => {
    const stepUpCode = params?.step_up_code;
    const queryParams = {
      days: params?.days,
    };
    const { data } = await api.get(
      `/collaboration/workspaces/${workspaceId}/shared/audit-export`,
      {
        params: queryParams,
        responseType: "blob",
        headers: {
          Accept: "text/csv",
          ...(stepUpCode ? { "X-Step-Up-Code": stepUpCode } : {}),
        },
      }
    );
    return data;
  },

  unshareData: async (
    workspaceId: number,
    permId: number
  ): Promise<void> => {
    await api.delete(
      `/collaboration/workspaces/${workspaceId}/shared/${permId}`
    );
  },

  // Portal
  getPortal: async (workspaceId: number): Promise<PortalView> => {
    const { data } = await api.get(
      `/collaboration/portal/${workspaceId}`
    );
    return data;
  },

  // Real-Time Presence & Locking
  getPresence: async (proposalId: number): Promise<DocumentPresence> => {
    const { data } = await api.get(
      `/collaboration/proposals/${proposalId}/presence`
    );
    return data;
  },

  lockSection: async (sectionId: number): Promise<SectionLock> => {
    const { data } = await api.post(
      `/collaboration/sections/${sectionId}/lock`
    );
    return data;
  },

  unlockSection: async (sectionId: number): Promise<void> => {
    await api.delete(`/collaboration/sections/${sectionId}/lock`);
  },

  // Inbox
  listInboxMessages: async (
    workspaceId: number,
    params?: { page?: number; page_size?: number }
  ): Promise<InboxListResponse> => {
    const { data } = await api.get(
      `/collaboration/workspaces/${workspaceId}/inbox`,
      { params }
    );
    return data;
  },

  sendInboxMessage: async (
    workspaceId: number,
    payload: {
      subject: string;
      body: string;
      message_type?: InboxMessageType;
      attachments?: string[] | null;
    }
  ): Promise<InboxMessage> => {
    const { data } = await api.post(
      `/collaboration/workspaces/${workspaceId}/inbox`,
      payload
    );
    return data;
  },

  markInboxMessageRead: async (
    workspaceId: number,
    messageId: number
  ): Promise<InboxMessage> => {
    const { data } = await api.patch(
      `/collaboration/workspaces/${workspaceId}/inbox/${messageId}/read`
    );
    return data;
  },

  deleteInboxMessage: async (
    workspaceId: number,
    messageId: number
  ): Promise<void> => {
    await api.delete(
      `/collaboration/workspaces/${workspaceId}/inbox/${messageId}`
    );
  },
};
