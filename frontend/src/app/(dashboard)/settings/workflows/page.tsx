"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { workflowApi } from "@/lib/api";
import type {
  WorkflowRule,
  WorkflowRuleCreate,
  WorkflowCondition,
  WorkflowAction,
  WorkflowExecution,
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

function emptyCondition(): WorkflowCondition {
  return { field: "", operator: "equals", value: "" };
}

function emptyAction(): WorkflowAction {
  return { action_type: "send_notification", params: {} };
}

export default function WorkflowsPage() {
  const [rules, setRules] = useState<WorkflowRule[]>([]);
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  // Form state
  const [formName, setFormName] = useState("");
  const [formTrigger, setFormTrigger] = useState<TriggerType>("rfp_created");
  const [formConditions, setFormConditions] = useState<WorkflowCondition[]>([emptyCondition()]);
  const [formActions, setFormActions] = useState<WorkflowAction[]>([emptyAction()]);
  const [formPriority, setFormPriority] = useState("0");
  const [saving, setSaving] = useState(false);

  const fetchRules = useCallback(async () => {
    try {
      setLoading(true);
      const data = await workflowApi.listRules();
      setRules(data.items);
    } catch (err) {
      console.error("Failed to load workflow rules", err);
      setError("Failed to load workflow rules.");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchExecutions = useCallback(async () => {
    try {
      const data = await workflowApi.listExecutions({ limit: 20 });
      setExecutions(data.items);
    } catch (err) {
      console.error("Failed to load executions", err);
    }
  }, []);

  useEffect(() => {
    fetchRules();
    fetchExecutions();
  }, [fetchRules, fetchExecutions]);

  const handleToggle = async (rule: WorkflowRule) => {
    try {
      await workflowApi.updateRule(rule.id, { is_enabled: !rule.is_enabled });
      setRules((prev) =>
        prev.map((r) => (r.id === rule.id ? { ...r, is_enabled: !r.is_enabled } : r))
      );
    } catch (err) {
      console.error("Failed to toggle rule", err);
      setError("Failed to toggle rule.");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await workflowApi.deleteRule(id);
      setRules((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      console.error("Failed to delete rule", err);
      setError("Failed to delete rule.");
    }
  };

  const handleTest = async (id: number) => {
    try {
      const result = await workflowApi.testRule(id);
      alert(`Test result: ${result.would_match} entities would match.`);
    } catch (err) {
      console.error("Failed to test rule", err);
      setError("Failed to test rule.");
    }
  };

  const resetForm = () => {
    setFormName("");
    setFormTrigger("rfp_created");
    setFormConditions([emptyCondition()]);
    setFormActions([emptyAction()]);
    setFormPriority("0");
    setShowForm(false);
  };

  const handleCreate = async () => {
    if (!formName.trim()) {
      setError("Rule name is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload: WorkflowRuleCreate = {
        name: formName.trim(),
        trigger_type: formTrigger,
        conditions: formConditions.filter((c) => c.field.trim()),
        actions: formActions.filter((a) => a.action_type),
        priority: parseInt(formPriority, 10) || 0,
      };
      const created = await workflowApi.createRule(payload);
      setRules((prev) => [created, ...prev]);
      resetForm();
    } catch (err) {
      console.error("Failed to create rule", err);
      setError("Failed to create rule.");
    } finally {
      setSaving(false);
    }
  };

  const updateCondition = (idx: number, patch: Partial<WorkflowCondition>) => {
    setFormConditions((prev) =>
      prev.map((c, i) => (i === idx ? { ...c, ...patch } : c))
    );
  };

  const updateAction = (idx: number, patch: Partial<WorkflowAction>) => {
    setFormActions((prev) =>
      prev.map((a, i) => (i === idx ? { ...a, ...patch } : a))
    );
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Workflow Rules"
        description="Automate actions when opportunities change"
      />

      <div className="flex-1 p-6 overflow-auto space-y-6">
        {error && <p className="text-destructive text-sm">{error}</p>}

        {/* Add Rule Button */}
        <div className="flex justify-end">
          <Button onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "Add Rule"}
          </Button>
        </div>

        {/* Create Rule Form */}
        {showForm && (
          <Card className="border border-border">
            <CardContent className="p-4 space-y-4">
              <p className="text-sm font-medium text-foreground">New Workflow Rule</p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input
                  className="rounded-md border border-border bg-background px-3 py-2 text-sm"
                  placeholder="Rule name"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                />
                <select
                  className="rounded-md border border-border bg-background px-3 py-2 text-sm"
                  value={formTrigger}
                  onChange={(e) => setFormTrigger(e.target.value as TriggerType)}
                >
                  {Object.entries(TRIGGER_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
                <input
                  className="rounded-md border border-border bg-background px-3 py-2 text-sm"
                  placeholder="Priority (0-99)"
                  type="number"
                  value={formPriority}
                  onChange={(e) => setFormPriority(e.target.value)}
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
                      value={typeof cond.value === "string" ? cond.value : String(cond.value)}
                      onChange={(e) => updateCondition(idx, { value: e.target.value })}
                    />
                    <button
                      className="text-muted-foreground hover:text-destructive text-sm"
                      onClick={() => setFormConditions((prev) => prev.filter((_, i) => i !== idx))}
                    >
                      Remove
                    </button>
                  </div>
                ))}
                <button
                  className="text-xs text-primary hover:underline"
                  onClick={() => setFormConditions((prev) => [...prev, emptyCondition()])}
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
                      value={action.params.value != null ? String(action.params.value) : ""}
                      onChange={(e) => updateAction(idx, { params: { ...action.params, value: e.target.value } })}
                    />
                    <button
                      className="text-muted-foreground hover:text-destructive text-sm"
                      onClick={() => setFormActions((prev) => prev.filter((_, i) => i !== idx))}
                    >
                      Remove
                    </button>
                  </div>
                ))}
                <button
                  className="text-xs text-primary hover:underline"
                  onClick={() => setFormActions((prev) => [...prev, emptyAction()])}
                >
                  + Add action
                </button>
              </div>

              <div className="flex gap-3">
                <Button onClick={handleCreate} disabled={saving}>
                  {saving ? "Creating..." : "Create Rule"}
                </Button>
                <Button variant="outline" onClick={resetForm}>
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Rules List */}
        {loading ? (
          <p className="text-sm text-muted-foreground">Loading rules...</p>
        ) : rules.length === 0 ? (
          <Card className="border border-border">
            <CardContent className="p-6 text-center">
              <p className="text-sm text-muted-foreground">
                No workflow rules configured yet. Click &quot;Add Rule&quot; to create one.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {rules.map((rule) => (
              <Card key={rule.id} className="border border-border">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => handleToggle(rule)}
                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                          rule.is_enabled ? "bg-primary" : "bg-muted"
                        }`}
                      >
                        <span
                          className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
                            rule.is_enabled ? "translate-x-4.5" : "translate-x-0.5"
                          }`}
                        />
                      </button>
                      <div>
                        <p className="text-sm font-medium text-foreground">{rule.name}</p>
                        <p className="text-xs text-muted-foreground">
                          Trigger: {TRIGGER_LABELS[rule.trigger_type]}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">
                        {rule.conditions?.length || 0} condition{rule.conditions?.length !== 1 ? "s" : ""}
                      </Badge>
                      <Badge variant="outline">
                        {rule.actions?.length || 0} action{rule.actions?.length !== 1 ? "s" : ""}
                      </Badge>
                      <Button variant="ghost" size="sm" onClick={() => handleTest(rule.id)}>
                        Test
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(rule.id)}>
                        Delete
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Execution History */}
        <div className="space-y-3">
          <p className="text-sm font-medium text-foreground">Recent Executions</p>
          {executions.length === 0 ? (
            <p className="text-xs text-muted-foreground">No executions yet.</p>
          ) : (
            <Card className="border border-border">
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left px-4 py-2 font-medium text-muted-foreground">Rule</th>
                      <th className="text-left px-4 py-2 font-medium text-muted-foreground">Entity</th>
                      <th className="text-left px-4 py-2 font-medium text-muted-foreground">Status</th>
                      <th className="text-left px-4 py-2 font-medium text-muted-foreground">Triggered</th>
                    </tr>
                  </thead>
                  <tbody>
                    {executions.map((ex) => (
                      <tr key={ex.id} className="border-b border-border last:border-0">
                        <td className="px-4 py-2">Rule #{ex.rule_id}</td>
                        <td className="px-4 py-2">{ex.entity_type} #{ex.entity_id}</td>
                        <td className="px-4 py-2">
                          <Badge
                            variant={
                              ex.status === "success" ? "success" : ex.status === "failed" ? "destructive" : "outline"
                            }
                          >
                            {ex.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-2 text-muted-foreground">
                          {new Date(ex.triggered_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
