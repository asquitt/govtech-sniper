"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CreditCard, ExternalLink, Sparkles } from "lucide-react";
import { PlanCard } from "@/components/subscription/plan-card";
import { UsageMeter } from "@/components/subscription/usage-meter";
import { subscriptionApi } from "@/lib/api";
import type { PlanDefinition, SubscriptionStatus, UsageStats } from "@/types";

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
        {/* Checkout result banners */}
        {checkoutResult === "success" && (
          <div className="flex items-center gap-2 rounded-lg border border-green-500/30 bg-green-500/10 px-4 py-3">
            <Sparkles className="h-5 w-5 text-green-600 flex-shrink-0" />
            <p className="text-sm font-medium text-green-700">
              Subscription activated! Your plan has been upgraded.
            </p>
          </div>
        )}
        {checkoutResult === "cancelled" && (
          <div className="flex items-center gap-2 rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-3">
            <p className="text-sm text-yellow-700">
              Checkout was cancelled. You can try again anytime.
            </p>
          </div>
        )}
        {checkoutError && (
          <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3">
            <p className="text-sm text-destructive">
              {checkoutError === "stripe_not_configured"
                ? "Payment processing is not yet configured. Please contact support."
                : checkoutError === "price_not_configured"
                  ? "This plan is not available for purchase yet."
                  : "An error occurred. Please try again."}
            </p>
          </div>
        )}

        {error && <p className="text-destructive text-sm">{error}</p>}

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
            <Card className="border border-border">
              <CardContent className="p-5 space-y-4">
                <div>
                  <p className="text-sm font-medium">Billing</p>
                  <p className="text-xs text-muted-foreground">
                    Manage your subscription and payment methods
                  </p>
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status</span>
                    <Badge
                      variant={
                        subStatus.status === "active"
                          ? "default"
                          : subStatus.status === "grace_period"
                            ? "warning"
                            : "secondary"
                      }
                    >
                      {subStatus.status === "free"
                        ? "Free Plan"
                        : subStatus.status === "active"
                          ? "Active"
                          : subStatus.status === "grace_period"
                            ? "Grace Period"
                            : "Expired"}
                    </Badge>
                  </div>
                  {subStatus.expires_at && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Renews</span>
                      <span className="text-foreground">
                        {new Date(subStatus.expires_at).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>

                {subStatus.has_stripe_customer && (
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={handleManageBilling}
                    disabled={portalLoading}
                  >
                    <CreditCard className="h-4 w-4 mr-2" />
                    {portalLoading ? "Opening..." : "Manage Billing"}
                    <ExternalLink className="h-3 w-3 ml-auto" />
                  </Button>
                )}

                {subStatus.status === "free" && !subStatus.has_subscription && (
                  <div className="rounded-md bg-primary/5 border border-primary/20 p-3">
                    <p className="text-xs font-medium text-primary">
                      Start a 14-day free trial — no credit card required
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Try any paid plan risk-free. Cancel anytime during the trial.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

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
