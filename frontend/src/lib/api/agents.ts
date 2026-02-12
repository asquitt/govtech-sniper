import { api } from "./client";
import type { AgentDescriptor, AgentRunResponse } from "@/types/agent";

export const agentsApi = {
  list: async (): Promise<AgentDescriptor[]> => {
    const { data } = await api.get("/agents/catalog");
    return data;
  },

  runResearch: async (rfpId: number): Promise<AgentRunResponse> => {
    const { data } = await api.post(`/agents/research/${rfpId}`);
    return data;
  },

  runCapturePlanning: async (rfpId: number): Promise<AgentRunResponse> => {
    const { data } = await api.post(`/agents/capture-planning/${rfpId}`);
    return data;
  },

  runProposalPrep: async (rfpId: number): Promise<AgentRunResponse> => {
    const { data } = await api.post(`/agents/proposal-prep/${rfpId}`);
    return data;
  },

  runCompetitiveIntel: async (rfpId: number): Promise<AgentRunResponse> => {
    const { data } = await api.post(`/agents/competitive-intel/${rfpId}`);
    return data;
  },
};
