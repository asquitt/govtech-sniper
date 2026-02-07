"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Circle } from "lucide-react";

interface AgentStep {
  step: string;
  status: string;
  summary: string;
}

interface AgentRunResult {
  run_id: string;
  agent_type: string;
  status: string;
  result: Record<string, unknown>;
}

interface AgentProgressProps {
  result: AgentRunResult;
}

export function AgentProgress({ result }: AgentProgressProps) {
  const steps = (result.result.steps as AgentStep[] | undefined) ?? [];
  const report =
    (result.result.report as string) ??
    (result.result.capture_plan as string) ??
    (result.result.prep_summary as string) ??
    null;

  const agentLabel = result.agent_type
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

  return (
    <div className="rounded-md border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-foreground">
          {agentLabel} Agent Run
        </p>
        <Badge
          variant={result.status === "completed" ? "default" : "secondary"}
          className="text-[10px]"
        >
          {result.status}
        </Badge>
      </div>

      <p className="text-[10px] text-muted-foreground">
        Run ID: {result.run_id}
      </p>

      {steps.length > 0 && (
        <div className="space-y-1.5">
          {steps.map((step) => (
            <div key={step.step} className="flex items-start gap-2">
              {step.status === "completed" ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-green-500 mt-0.5 shrink-0" />
              ) : (
                <Circle className="w-3.5 h-3.5 text-muted-foreground mt-0.5 shrink-0" />
              )}
              <span className="text-xs text-foreground">{step.summary}</span>
            </div>
          ))}
        </div>
      )}

      {report && (
        <div className="rounded bg-secondary/50 p-2">
          <p className="text-xs text-foreground whitespace-pre-line">
            {report}
          </p>
        </div>
      )}
    </div>
  );
}
