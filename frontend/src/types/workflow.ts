export type TriggerType = "rfp_created" | "stage_changed" | "deadline_approaching" | "score_threshold";
export type ExecutionStatus = "success" | "failed" | "skipped";

export interface WorkflowCondition {
  field: string;
  operator: "equals" | "gt" | "lt" | "contains" | "in_list";
  value: string | number | string[];
}

export interface WorkflowAction {
  action_type: "move_stage" | "assign_user" | "send_notification" | "add_tag";
  params: Record<string, string | number>;
}

export interface WorkflowRule {
  id: number;
  user_id: number;
  name: string;
  is_enabled: boolean;
  trigger_type: TriggerType;
  conditions: WorkflowCondition[];
  actions: WorkflowAction[];
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRuleCreate {
  name: string;
  trigger_type: TriggerType;
  conditions: WorkflowCondition[];
  actions: WorkflowAction[];
  priority?: number;
}

export interface WorkflowExecution {
  id: number;
  rule_id: number;
  triggered_at: string;
  entity_type: string;
  entity_id: number;
  status: ExecutionStatus;
  result: Record<string, unknown>;
  completed_at: string | null;
}
