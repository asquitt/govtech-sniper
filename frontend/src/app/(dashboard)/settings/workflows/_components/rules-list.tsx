"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { WorkflowRule, TriggerType } from "@/types/workflow";

const TRIGGER_LABELS: Record<TriggerType, string> = {
  rfp_created: "RFP Created",
  stage_changed: "Stage Changed",
  deadline_approaching: "Deadline Approaching",
  score_threshold: "Score Threshold",
};

export interface RulesListProps {
  rules: WorkflowRule[];
  loading: boolean;
  onToggle: (rule: WorkflowRule) => void;
  onTest: (id: number) => void;
  onDelete: (id: number) => void;
}

export function RulesList({ rules, loading, onToggle, onTest, onDelete }: RulesListProps) {
  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading rules...</p>;
  }

  if (rules.length === 0) {
    return (
      <Card className="border border-border">
        <CardContent className="p-6 text-center">
          <p className="text-sm text-muted-foreground">
            No workflow rules configured yet. Click &quot;Add Rule&quot; to create one.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {rules.map((rule) => (
        <Card key={rule.id} className="border border-border">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button
                  role="switch"
                  aria-checked={rule.is_enabled}
                  aria-label={`Toggle ${rule.name}`}
                  onClick={() => onToggle(rule)}
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
                <Button variant="ghost" size="sm" onClick={() => onTest(rule.id)}>
                  Test
                </Button>
                <Button variant="ghost" size="sm" onClick={() => onDelete(rule.id)}>
                  Delete
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
