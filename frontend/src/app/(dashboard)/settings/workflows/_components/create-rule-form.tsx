"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type {
  WorkflowCondition,
  WorkflowAction,
  TriggerType,
} from "@/types/workflow";

const TRIGGER_LABELS: Record<TriggerType, string> = {
  rfp_created: "RFP Created",
  stage_changed: "Stage Changed",
  deadline_approaching: "Deadline Approaching",
  score_threshold: "Score Threshold",
};

const OPERATOR_OPTIONS = ["equals", "gt", "lt", "contains", "in_list"] as const;
const ACTION_TYPE_OPTIONS = [
  "move_stage",
  "assign_user",
  "send_notification",
  "add_tag",
  "evaluate_teaming",
] as const;

const ACTION_LABELS: Record<string, string> = {
  move_stage: "Move Stage",
  assign_user: "Assign User",
  send_notification: "Send Notification",
  add_tag: "Add Tag",
  evaluate_teaming: "Evaluate Teaming",
};

export interface CreateRuleFormProps {
  formName: string;
  formTrigger: TriggerType;
  formConditions: WorkflowCondition[];
  formActions: WorkflowAction[];
  formPriority: string;
  saving: boolean;
  onNameChange: (value: string) => void;
  onTriggerChange: (value: TriggerType) => void;
  onConditionsChange: (conditions: WorkflowCondition[]) => void;
  onActionsChange: (actions: WorkflowAction[]) => void;
  onPriorityChange: (value: string) => void;
  onCreate: () => void;
  onCancel: () => void;
}

export function CreateRuleForm({
  formName,
  formTrigger,
  formConditions,
  formActions,
  formPriority,
  saving,
  onNameChange,
  onTriggerChange,
  onConditionsChange,
  onActionsChange,
  onPriorityChange,
  onCreate,
  onCancel,
}: CreateRuleFormProps) {
  const updateCondition = (idx: number, patch: Partial<WorkflowCondition>) => {
    onConditionsChange(
      formConditions.map((c, i) => (i === idx ? { ...c, ...patch } : c))
    );
  };

  const updateAction = (idx: number, patch: Partial<WorkflowAction>) => {
    onActionsChange(
      formActions.map((a, i) => (i === idx ? { ...a, ...patch } : a))
    );
  };

  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-4">
        <p className="text-sm font-medium text-foreground">New Workflow Rule</p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input
            className="rounded-md border border-border bg-background px-3 py-2 text-sm"
            placeholder="Rule name"
            aria-label="Rule name"
            value={formName}
            onChange={(e) => onNameChange(e.target.value)}
          />
          <select
            className="rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={formTrigger}
            onChange={(e) => onTriggerChange(e.target.value as TriggerType)}
          >
            {Object.entries(TRIGGER_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
          <input
            className="rounded-md border border-border bg-background px-3 py-2 text-sm"
            placeholder="Priority (0-99)"
            aria-label="Priority"
            type="number"
            value={formPriority}
            onChange={(e) => onPriorityChange(e.target.value)}
          />
        </div>

        {/* Conditions */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Conditions</p>
          {formConditions.map((cond, idx) => (
            <div key={idx} className="flex gap-2 items-center">
              <input
                className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
                placeholder="Field (e.g. score)"
                aria-label="Condition field"
                value={cond.field}
                onChange={(e) => updateCondition(idx, { field: e.target.value })}
              />
              <select
                className="rounded-md border border-border bg-background px-3 py-2 text-sm"
                value={cond.operator}
                onChange={(e) => updateCondition(idx, { operator: e.target.value as WorkflowCondition["operator"] })}
              >
                {OPERATOR_OPTIONS.map((op) => (
                  <option key={op} value={op}>{op}</option>
                ))}
              </select>
              <input
                className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
                placeholder="Value"
                aria-label="Condition value"
                value={typeof cond.value === "string" ? cond.value : String(cond.value)}
                onChange={(e) => updateCondition(idx, { value: e.target.value })}
              />
              <button
                className="text-muted-foreground hover:text-destructive text-sm"
                onClick={() => onConditionsChange(formConditions.filter((_, i) => i !== idx))}
              >
                Remove
              </button>
            </div>
          ))}
          <button
            className="text-xs text-primary hover:underline"
            onClick={() => onConditionsChange([...formConditions, { field: "", operator: "equals", value: "" }])}
          >
            + Add condition
          </button>
        </div>

        {/* Actions */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Actions</p>
          {formActions.map((action, idx) => (
            <div key={idx} className="flex gap-2 items-center">
              <select
                className="rounded-md border border-border bg-background px-3 py-2 text-sm"
                value={action.action_type}
                onChange={(e) => updateAction(idx, { action_type: e.target.value as WorkflowAction["action_type"] })}
              >
                {ACTION_TYPE_OPTIONS.map((at) => (
                  <option key={at} value={at}>{ACTION_LABELS[at]}</option>
                ))}
              </select>
              <input
                className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
                placeholder="Param value"
                aria-label="Action parameter value"
                value={action.params.value != null ? String(action.params.value) : ""}
                onChange={(e) => updateAction(idx, { params: { ...action.params, value: e.target.value } })}
              />
              <button
                className="text-muted-foreground hover:text-destructive text-sm"
                onClick={() => onActionsChange(formActions.filter((_, i) => i !== idx))}
              >
                Remove
              </button>
            </div>
          ))}
          <button
            className="text-xs text-primary hover:underline"
            onClick={() => onActionsChange([...formActions, { action_type: "send_notification", params: {} }])}
          >
            + Add action
          </button>
        </div>

        <div className="flex gap-3">
          <Button onClick={onCreate} disabled={saving}>
            {saving ? "Creating..." : "Create Rule"}
          </Button>
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
