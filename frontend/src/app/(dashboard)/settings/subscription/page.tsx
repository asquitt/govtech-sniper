"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ExternalLink } from "lucide-react";
import { PlanCard } from "@/components/subscription/plan-card";
import { UsageMeter } from "@/components/subscription/usage-meter";
import { UpgradeNudge } from "@/components/subscription/upgrade-nudge";
import { subscriptionApi } from "@/lib/api";
import type { PlanDefinition, SubscriptionStatus, UsageStats } from "@/types";
import { CheckoutBanners } from "./_components/checkout-banners";
import { BillingCard } from "./_components/billing-card";
import { BillingToggle } from "./_components/billing-toggle";

export default function SubscriptionPage() {
  const searchParams = useSearchParams();
  const [plans, setPlans] = useState<PlanDefinition[]>([]);
  const [currentPlan, setCurrentPlan] = useState<PlanDefinition | null>(null);
  const [subStatus, setSubStatus] = useState<SubscriptionStatus | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [annual, setAnnual] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);

  const checkoutResult = searchParams.get("checkout");
  const checkoutError = searchParams.get("error");

  const getNextTier = (tier: string | null | undefined) => {
    if (tier === "free") return "starter";
    if (tier === "starter") return "professional";
    if (tier === "professional") return "enterprise";
    return "enterprise";
  };

  const getUsageHotspot = (usageStats: UsageStats | null) => {
    if (!usageStats) return null;
    const rows = [
      {
        label: "RFP tracking quota",
        used: usageStats.rfps_used,
        limit: usageStats.rfps_limit,
      },
      {
        label: "Proposal quota",
        used: usageStats.proposals_used,
        limit: usageStats.proposals_limit,
      },
      {
        label: "Daily API request quota",
        used: usageStats.api_calls_used,
        limit: usageStats.api_calls_limit,
      },
    ].filter((row) => row.limit >= 0);

    let winner: { label: string; percent: number } | null = null;
    for (const row of rows) {
      const percent = row.limit === 0 ? 1 : row.used / row.limit;
      if (!winner || percent > winner.percent) {
        winner = { label: row.label, percent };
      }
    }
    return winner;
  };

  const usageHotspot = getUsageHotspot(usage);
  const shouldShowUpgradeNudge =
    !!usageHotspot &&
    usageHotspot.percent >= 0.8 &&
    currentPlan?.tier !== "enterprise";

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [planList, current, usageData, statusData] = await Promise.all([
        subscriptionApi.listPlans(),
        subscriptionApi.currentPlan(),
        subscriptionApi.usage(),
        subscriptionApi.status(),
      ]);
      setPlans(planList);
      setCurrentPlan(current);
      setUsage(usageData);
      setSubStatus(statusData);
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
      if (result.checkout_url) {
        window.open(result.checkout_url, "_blank");
      }
    } catch (err) {
      console.error("Failed to start checkout", err);
      setError("Failed to start checkout. Please try again.");
    }
  };

  const handleManageBilling = async () => {
    try {
      setPortalLoading(true);
      const result = await subscriptionApi.portal();
      if (result.portal_url) {
        window.open(result.portal_url, "_blank");
      }
    } catch (err) {
      console.error("Failed to open billing portal", err);
      setError("Failed to open billing portal. Please try again.");
    } finally {
      setPortalLoading(false);
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
        <CheckoutBanners
          checkoutResult={checkoutResult}
          checkoutError={checkoutError}
        />

        {error && <p className="text-destructive text-sm">{error}</p>}

        <div className="flex justify-end">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/free-tier">
              View Free Tier Landing Page
              <ExternalLink className="h-3 w-3" />
            </Link>
          </Button>
        </div>

        {shouldShowUpgradeNudge && (
          <UpgradeNudge
            feature={
              usageHotspot.percent >= 1
                ? `${usageHotspot.label} is at its limit`
                : `${usageHotspot.label} is nearing its limit`
            }
            requiredTier={getNextTier(currentPlan?.tier)}
          />
        )}

        {/* Subscription Status + Usage */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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

          {subStatus && (
            <BillingCard
              subStatus={subStatus}
              portalLoading={portalLoading}
              onManageBilling={handleManageBilling}
            />
          )}
        </div>

        <BillingToggle annual={annual} onToggle={setAnnual} />

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
