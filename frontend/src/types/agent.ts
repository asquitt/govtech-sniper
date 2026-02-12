export interface AgentDescriptor {
  id: string;
  name: string;
  description: string;
}

export interface AgentRunResponse {
  agent: string;
  rfp_id: number;
  summary: string;
  actions_taken: string[];
  artifacts: Record<string, unknown>;
}
