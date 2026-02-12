import api from "./client";
import type {
  AdminCapabilityHealth,
  OrgMemberInvitation,
  OrgAuditEvent,
  OrgMember,
  OrgRole,
  OrgUsageAnalytics,
  OrganizationDetails,
  SSOProviderType,
} from "@/types";

// =============================================================================
// Admin & Organization Endpoints
// =============================================================================

export const adminApi = {
  // Organization
  createOrganization: async (params: {
    name: string;
    slug: string;
    domain?: string;
    billing_email?: string;
  }): Promise<{ id: number; name: string; slug: string }> => {
    const { data } = await api.post("/admin/organizations", params);
    return data;
  },

  getOrganization: async (): Promise<OrganizationDetails> => {
    const { data } = await api.get("/admin/organization");
    return data;
  },

  updateOrganization: async (params: {
    name?: string;
    domain?: string;
    billing_email?: string;
    sso_enabled?: boolean;
    sso_provider?: SSOProviderType;
    sso_enforce?: boolean;
    sso_auto_provision?: boolean;
    logo_url?: string;
    primary_color?: string;
    ip_allowlist?: string[];
    data_retention_days?: number;
  }): Promise<{ status: string }> => {
    const { data } = await api.patch("/admin/organization", params);
    return data;
  },

  // Members
  listMembers: async (): Promise<{ members: OrgMember[]; total: number }> => {
    const { data } = await api.get("/admin/members");
    return data;
  },

  inviteMember: async (payload: {
    email: string;
    role?: OrgRole;
    expires_in_days?: number;
  }): Promise<OrgMemberInvitation> => {
    const { data } = await api.post("/admin/members/invite", payload);
    return data;
  },

  listMemberInvitations: async (): Promise<OrgMemberInvitation[]> => {
    const { data } = await api.get("/admin/member-invitations");
    return data;
  },

  activateMemberInvitation: async (
    invitationId: number
  ): Promise<OrgMemberInvitation> => {
    const { data } = await api.post(
      `/admin/member-invitations/${invitationId}/activate`
    );
    return data;
  },

  updateMemberRole: async (
    userId: number,
    role: OrgRole
  ): Promise<{ status: string }> => {
    const { data } = await api.patch(`/admin/members/${userId}/role`, {
      role,
    });
    return data;
  },

  deactivateMember: async (
    userId: number
  ): Promise<{ status: string }> => {
    const { data } = await api.post(`/admin/members/${userId}/deactivate`);
    return data;
  },

  reactivateMember: async (
    userId: number
  ): Promise<{ status: string }> => {
    const { data } = await api.post(`/admin/members/${userId}/reactivate`);
    return data;
  },

  // Usage Analytics
  getUsageAnalytics: async (
    days?: number
  ): Promise<OrgUsageAnalytics> => {
    const { data } = await api.get("/admin/usage", {
      params: days ? { days } : undefined,
    });
    return data;
  },

  // Org Audit Log
  getAuditLog: async (params?: {
    action?: string;
    entity_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ events: OrgAuditEvent[]; total: number }> => {
    const { data } = await api.get("/admin/audit", { params });
    return data;
  },

  getCapabilityHealth: async (): Promise<AdminCapabilityHealth> => {
    const { data } = await api.get("/admin/capability-health");
    return data;
  },
};
