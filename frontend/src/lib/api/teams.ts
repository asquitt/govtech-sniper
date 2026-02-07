import api from "./client";

// =============================================================================
// Team Types (local to api module)
// =============================================================================

export type TeamRole = "owner" | "admin" | "member" | "viewer";

export interface Team {
  id: number;
  name: string;
  description: string | null;
  owner_id: number;
  member_count: number;
  your_role: TeamRole;
  created_at: string;
}

export interface TeamMember {
  user_id: number;
  email: string;
  full_name: string | null;
  role: TeamRole;
  joined_at: string | null;
}

export interface Comment {
  id: number;
  content: string;
  user_id: number;
  user_name: string;
  parent_id: number | null;
  is_resolved: boolean;
  created_at: string;
}

// =============================================================================
// Team Endpoints
// =============================================================================

export const teamApi = {
  list: async (): Promise<Team[]> => {
    const { data } = await api.get("/teams");
    return data;
  },

  create: async (team: {
    name: string;
    description?: string;
  }): Promise<Team> => {
    const { data } = await api.post("/teams", team);
    return data;
  },

  get: async (
    teamId: number
  ): Promise<Team & { members: TeamMember[] }> => {
    const { data } = await api.get(`/teams/${teamId}`);
    return data;
  },

  invite: async (
    teamId: number,
    email: string,
    role: TeamRole = "member"
  ): Promise<{ message: string; invitation_token?: string }> => {
    const { data } = await api.post(`/teams/${teamId}/invite`, { email, role });
    return data;
  },

  removeMember: async (teamId: number, userId: number): Promise<void> => {
    await api.delete(`/teams/${teamId}/members/${userId}`);
  },

  updateMemberRole: async (
    teamId: number,
    userId: number,
    role: TeamRole
  ): Promise<{ message: string; user_id: number; role: TeamRole }> => {
    const { data } = await api.patch(`/teams/${teamId}/members/${userId}`, {
      role,
    });
    return data;
  },

  // Comments
  getComments: async (
    proposalId: number,
    sectionId: number
  ): Promise<Comment[]> => {
    const { data } = await api.get(
      `/teams/proposals/${proposalId}/sections/${sectionId}/comments`
    );
    return data;
  },

  addComment: async (
    proposalId: number,
    sectionId: number,
    content: string,
    parentId?: number
  ): Promise<Comment> => {
    const { data } = await api.post(
      `/teams/proposals/${proposalId}/sections/${sectionId}/comments`,
      { content, parent_id: parentId }
    );
    return data;
  },

  resolveComment: async (commentId: number): Promise<void> => {
    await api.post(`/teams/comments/${commentId}/resolve`);
  },
};
