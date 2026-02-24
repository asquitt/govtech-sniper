"use client";

import React, { useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { workflowApi } from "@/lib/api";
import { useAsyncData } from "@/hooks/use-async-data";
import type {
  WorkflowRule,
  WorkflowRuleCreate,
  WorkflowCondition,
  WorkflowAction,
  WorkflowExecution,
  TriggerType,
} from "@/types/workflow";
import { CreateRuleForm } from "./_components/create-rule-form";
import { RulesList } from "./_components/rules-list";
import { ExecutionHistory } from "./_components/execution-history";

function emptyCondition(): WorkflowCondition {
  return { field: "", operator: "equals", value: "" };
}

function emptyAction(): WorkflowAction {
  return { action_type: "send_notification", params: {} };
}

export default function WorkflowsPage() {
  interface WorkflowData {
    rules: WorkflowRule[];
    executions: WorkflowExecution[];
  }

  const { data, loading, error: fetchError, refetch } = useAsyncData<WorkflowData>(
    async () => {
      const [rulesData, execData] = await Promise.all([
        workflowApi.listRules(),
        workflowApi.listExecutions({ limit: 20 }).catch(() => ({ items: [] })),
      ]);
      return { rules: rulesData.items, executions: execData.items };
    },
    [],
  );

  const rules = data?.rules ?? [];
  const executions = data?.executions ?? [];

  const [actionError, setActionError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const error = fetchError ? fetchError.message : actionError;

  // Form state
  const [formName, setFormName] = useState("");
  const [formTrigger, setFormTrigger] = useState<TriggerType>("rfp_created");
  const [formConditions, setFormConditions] = useState<WorkflowCondition[]>([emptyCondition()]);
  const [formActions, setFormActions] = useState<WorkflowAction[]>([emptyAction()]);
  const [formPriority, setFormPriority] = useState("0");
  const [saving, setSaving] = useState(false);

  const handleToggle = async (rule: WorkflowRule) => {
    try {
      await workflowApi.updateRule(rule.id, { is_enabled: !rule.is_enabled });
      await refetch();
    } catch (err) {
      console.error("Failed to toggle rule", err);
      setActionError("Failed to toggle rule.");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await workflowApi.deleteRule(id);
      await refetch();
    } catch (err) {
      console.error("Failed to delete rule", err);
      setActionError("Failed to delete rule.");
    }
  };

  const handleTest = async (id: number) => {
    try {
      const result = await workflowApi.testRule(id);
      alert(`Test result: ${result.would_match} entities would match.`);
    } catch (err) {
      console.error("Failed to test rule", err);
      setActionError("Failed to test rule.");
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
      setActionError("Rule name is required.");
      return;
    }
    setSaving(true);
    setActionError(null);
    try {
      const payload: WorkflowRuleCreate = {
        name: formName.trim(),
        trigger_type: formTrigger,
        conditions: formConditions.filter((c) => c.field.trim()),
        actions: formActions.filter((a) => a.action_type),
        priority: parseInt(formPriority, 10) || 0,
      };
      await workflowApi.createRule(payload);
      resetForm();
      await refetch();
    } catch (err) {
      console.error("Failed to create rule", err);
      setActionError("Failed to create rule.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Workflow Rules"
        description="Automate actions when opportunities change"
      />

      <div className="flex-1 p-6 overflow-auto space-y-6">
        {error && <p className="text-destructive text-sm">{error}</p>}

        <div className="flex justify-end">
          <Button onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "Add Rule"}
          </Button>
        </div>

        {showForm && (
          <CreateRuleForm
            formName={formName}
            formTrigger={formTrigger}
            formConditions={formConditions}
            formActions={formActions}
            formPriority={formPriority}
            saving={saving}
            onNameChange={setFormName}
            onTriggerChange={setFormTrigger}
            onConditionsChange={setFormConditions}
            onActionsChange={setFormActions}
            onPriorityChange={setFormPriority}
            onCreate={handleCreate}
            onCancel={resetForm}
          />
        )}

        <RulesList
          rules={rules}
          loading={loading}
          onToggle={handleToggle}
          onTest={handleTest}
          onDelete={handleDelete}
        />

        <ExecutionHistory executions={executions} />
      </div>
    </div>
  );
}
