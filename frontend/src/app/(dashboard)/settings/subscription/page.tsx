"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PlanCard } from "@/components/subscription/plan-card";
import { UsageMeter } from "@/components/subscription/usage-meter";
import { subscriptionApi } from "@/lib/api";
import type { PlanDefinition, UsageStats } from "@/types";

export default function SubscriptionPage() {
  const [plans, setPlans] = useState<PlanDefinition[]>([]);
  const [currentPlan, setCurrentPlan] = useState<PlanDefinition | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [annual, setAnnual] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [planList, current, usageData] = await Promise.all([
        subscriptionApi.listPlans(),
        subscriptionApi.currentPlan(),
        subscriptionApi.usage(),
      ]);
      setPlans(planList);
      setCurrentPlan(current);
      setUsage(usageData);
    } catch (err) {
      console.error("Failed to load subscription data", err);
      setError("Failed to load subscription information.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSelectPlan = async (tier: string) => {
    try {
      const result = await subscriptionApi.checkout(tier, annual);
      window.open(result.checkout_url, "_blank");
    } catch (err) {
      console.error("Failed to start checkout", err);
      setError("Failed to start checkout. Please try again.");
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <Header
          title="Subscription"
          description="Manage your plan and usage"
        />
        <div className="flex-1 p-6 space-y-4">
          <div className="animate-pulse h-6 w-48 bg-muted rounded" />
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="animate-pulse h-64 bg-muted rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Subscription"
        description="Manage your plan and usage"
      />

      <div className="flex-1 p-6 overflow-auto space-y-6">
        {error && <p className="text-destructive text-sm">{error}</p>}

        {/* Usage Section */}
        {usage && (
          <Card className="border border-border">
            <CardContent className="p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Current Usage</p>
                  <p className="text-xs text-muted-foreground">
                    Your resource consumption this period
                  </p>
                </div>
                {currentPlan && (
                  <Badge variant="default">{currentPlan.label} Plan</Badge>
                )}
              </div>
              <UsageMeter usage={usage} />
            </CardContent>
          </Card>
        )}

        {/* Billing Toggle */}
        <div className="flex items-center justify-center gap-3">
          <span
            className={`text-sm cursor-pointer ${!annual ? "font-semibold text-foreground" : "text-muted-foreground"}`}
            onClick={() => setAnnual(false)}
          >
            Monthly
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={annual}
            onClick={() => setAnnual(!annual)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              annual ? "bg-primary" : "bg-muted"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                annual ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
          <span
            className={`text-sm cursor-pointer ${annual ? "font-semibold text-foreground" : "text-muted-foreground"}`}
            onClick={() => setAnnual(true)}
          >
            Annual
            <Badge variant="success" className="ml-1.5 text-[10px]">
              Save 20%
            </Badge>
          </span>
        </div>

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {plans.map((plan) => (
            <PlanCard
              key={plan.tier}
              plan={plan}
              currentTier={currentPlan?.tier ?? "free"}
              annual={annual}
              onSelect={handleSelectPlan}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
