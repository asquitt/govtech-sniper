import { api } from "./client";
import type { WorkflowRule, WorkflowRuleCreate, WorkflowExecution } from "@/types/workflow";

export const workflowApi = {
  createRule: (data: WorkflowRuleCreate) =>
    api.post<WorkflowRule>("/workflows/rules", data).then((r) => r.data),

  listRules: () =>
    api.get<{ items: WorkflowRule[]; total: number }>("/workflows/rules").then((r) => r.data),

  getRule: (id: number) =>
    api.get<WorkflowRule>(`/workflows/rules/${id}`).then((r) => r.data),

  updateRule: (id: number, data: Partial<WorkflowRuleCreate> & { is_enabled?: boolean }) =>
    api.patch<WorkflowRule>(`/workflows/rules/${id}`, data).then((r) => r.data),

  deleteRule: (id: number) =>
    api.delete(`/workflows/rules/${id}`).then((r) => r.data),

  testRule: (id: number) =>
    api.post<{ would_match: number; sample_results: unknown[] }>(`/workflows/rules/${id}/test`).then((r) => r.data),

  listExecutions: (params?: { rule_id?: number; limit?: number; offset?: number }) =>
    api.get<{ items: WorkflowExecution[]; total: number }>("/workflows/executions", { params }).then((r) => r.data),

  execute: (payload: {
    trigger_type: "rfp_created" | "stage_changed" | "deadline_approaching" | "score_threshold";
    entity_type: string;
    entity_id: number;
    context?: Record<string, unknown>;
  }) =>
    api
      .post<{ executions: WorkflowExecution[]; total: number }>("/workflows/execute", payload)
      .then((r) => r.data),
};
