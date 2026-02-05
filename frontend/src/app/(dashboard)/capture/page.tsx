"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { captureApi, rfpApi } from "@/lib/api";
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

export default function CapturePage() {
  const [rfps, setRfps] = useState<RFPListItem[]>([]);
  const [plans, setPlans] = useState<CapturePlanListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [rfpList, planList] = await Promise.all([
        rfpApi.list({ limit: 100 }),
        captureApi.listPlans(),
      ]);
      setRfps(rfpList);
      setPlans(planList);
    } catch (err) {
      console.error("Failed to load capture data", err);
      setError("Failed to load capture data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const planByRfp = useMemo(() => {
    const map = new Map<number, CapturePlanListItem>();
    plans.forEach((plan) => map.set(plan.rfp_id, plan));
    return map;
  }, [plans]);

  const handleCreatePlan = async (rfpId: number) => {
    try {
      await captureApi.createPlan({ rfp_id: rfpId });
      await fetchData();
    } catch (err) {
      console.error("Failed to create capture plan", err);
      setError("Failed to create capture plan.");
    }
  };

  const handleUpdatePlan = async (
    planId: number,
    updates: Partial<{ stage: CaptureStage; bid_decision: BidDecision }>
  ) => {
    try {
      await captureApi.updatePlan(planId, updates);
      await fetchData();
    } catch (err) {
      console.error("Failed to update capture plan", err);
      setError("Failed to update capture plan.");
    }
  };

  if (error && !isLoading) {
    return (
      <div className="flex flex-col h-full">
        <Header
          title="Capture"
          description="Track bid decisions, gate reviews, and teaming partners"
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={fetchData}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Capture"
        description="Track bid decisions, gate reviews, and teaming partners"
      />

      <div className="flex-1 p-6 overflow-hidden">
        <div className="grid grid-cols-3 gap-4 mb-6">
          <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Total Opportunities</p>
              <p className="text-2xl font-bold text-primary">{rfps.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-accent/5 to-accent/10 border-accent/20">
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Capture Plans</p>
              <p className="text-2xl font-bold text-accent">{plans.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-warning/5 to-warning/10 border-warning/20">
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Pending Decisions</p>
              <p className="text-2xl font-bold text-warning">
                {plans.filter((plan) => plan.bid_decision === "pending").length}
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-border text-sm font-medium">
            Capture Pipeline
          </div>
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
                            handleUpdatePlan(plan.id, {
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
                            handleUpdatePlan(plan.id, {
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
                    <Button onClick={() => handleCreatePlan(rfp.id)}>
                      Create Capture Plan
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
