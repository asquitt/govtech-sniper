"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type {
  CapturePlanListItem,
  CaptureStage,
  BidDecision,
  RFPListItem,
} from "@/types";

const stageOptions: { value: CaptureStage; label: string }[] = [
  { value: "identified", label: "Identified" },
  { value: "qualified", label: "Qualified" },
  { value: "pursuit", label: "Pursuit" },
  { value: "proposal", label: "Proposal" },
  { value: "submitted", label: "Submitted" },
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" },
];

const decisionOptions: { value: BidDecision; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "bid", label: "Bid" },
  { value: "no_bid", label: "No Bid" },
];

interface CapturePipelineProps {
  rfps: RFPListItem[];
  planByRfp: Map<number, CapturePlanListItem>;
  plansByStage: Map<CaptureStage, CapturePlanListItem[]>;
  onCreatePlan: (rfpId: number) => Promise<void>;
  onUpdatePlan: (
    planId: number,
    updates: Partial<{ stage: CaptureStage; bid_decision: BidDecision }>
  ) => Promise<void>;
}

export function CapturePipeline({
  rfps,
  planByRfp,
  plansByStage,
  onCreatePlan,
  onUpdatePlan,
}: CapturePipelineProps) {
  const [viewMode, setViewMode] = useState<"list" | "kanban">("list");

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between text-sm font-medium">
        <span>Capture Pipeline</span>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant={viewMode === "list" ? "default" : "outline"}
            onClick={() => setViewMode("list")}
          >
            List
          </Button>
          <Button
            size="sm"
            variant={viewMode === "kanban" ? "default" : "outline"}
            onClick={() => setViewMode("kanban")}
          >
            Kanban
          </Button>
        </div>
      </div>

      {viewMode === "list" ? (
        <div className="divide-y divide-border">
          {rfps.map((rfp) => {
            const plan = planByRfp.get(rfp.id);
            return (
              <div key={rfp.id} className="px-4 py-4 flex flex-col gap-3">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-base font-semibold text-foreground">
                      {rfp.title}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {rfp.agency || "Unknown agency"}
                    </p>
                  </div>
                  {plan ? (
                    <Badge variant="outline">Plan Active</Badge>
                  ) : (
                    <Badge variant="destructive">No Plan</Badge>
                  )}
                </div>

                {plan ? (
                  <div className="flex flex-wrap items-center gap-4">
                    <label className="text-sm text-muted-foreground">
                      Stage
                      <select
                        className="ml-2 rounded-md border border-border bg-background px-2 py-1 text-sm"
                        value={plan.stage}
                        onChange={(e) =>
                          onUpdatePlan(plan.id, {
                            stage: e.target.value as CaptureStage,
                          })
                        }
                      >
                        {stageOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-sm text-muted-foreground">
                      Decision
                      <select
                        className="ml-2 rounded-md border border-border bg-background px-2 py-1 text-sm"
                        value={plan.bid_decision}
                        onChange={(e) =>
                          onUpdatePlan(plan.id, {
                            bid_decision: e.target.value as BidDecision,
                          })
                        }
                      >
                        {decisionOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <span className="text-sm text-muted-foreground">
                      Win Probability: {plan.win_probability ?? "N/A"}%
                    </span>
                  </div>
                ) : (
                  <Button onClick={() => onCreatePlan(rfp.id)}>
                    Create Capture Plan
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="grid gap-4 p-4 md:grid-cols-3 lg:grid-cols-4">
          {stageOptions.map((stage) => {
            const stagePlans = plansByStage.get(stage.value) || [];
            return (
              <div
                key={stage.value}
                className="rounded-lg border border-border bg-background/40"
              >
                <div className="px-3 py-2 border-b border-border text-xs font-medium uppercase text-muted-foreground">
                  {stage.label} ({stagePlans.length})
                </div>
                <div className="space-y-2 p-3">
                  {stagePlans.length === 0 ? (
                    <p className="text-xs text-muted-foreground">
                      No plans in this stage.
                    </p>
                  ) : (
                    stagePlans.map((plan) => (
                      <div
                        key={plan.id}
                        className="rounded-md border border-border bg-card px-3 py-2 text-sm space-y-2"
                      >
                        <div>
                          <p className="font-medium text-foreground">
                            {plan.rfp_title || `RFP ${plan.rfp_id}`}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {plan.rfp_agency || "Unknown agency"}
                          </p>
                        </div>
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>Decision: {plan.bid_decision}</span>
                          <span>Win: {plan.win_probability ?? "N/A"}%</span>
                        </div>
                        <select
                          className="w-full rounded-md border border-border bg-background px-2 py-1 text-xs"
                          value={plan.stage}
                          onChange={(e) =>
                            onUpdatePlan(plan.id, {
                              stage: e.target.value as CaptureStage,
                            })
                          }
                        >
                          {stageOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              Move to {option.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
