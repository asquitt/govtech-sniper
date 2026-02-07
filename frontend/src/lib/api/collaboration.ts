import api from "./client";
import type {
  SharedWorkspace,
  WorkspaceInvitation,
  WorkspaceMember,
  SharedDataPermission,
  PortalView,
  SharedDataType,
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

  // Data sharing
  shareData: async (
    workspaceId: number,
    payload: { data_type: SharedDataType; entity_id: number }
  ): Promise<SharedDataPermission> => {
    const { data } = await api.post(
      `/collaboration/workspaces/${workspaceId}/share`,
      payload
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
};
