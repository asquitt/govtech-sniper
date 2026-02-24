"use client";

import React from "react";
import { CreditCard, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { SubscriptionStatus } from "@/types";

export interface BillingCardProps {
  subStatus: SubscriptionStatus;
  portalLoading: boolean;
  onManageBilling: () => void;
}

export function BillingCard({ subStatus, portalLoading, onManageBilling }: BillingCardProps) {
  return (
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
            onClick={onManageBilling}
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
              Start a 14-day free trial -- no credit card required
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Try any paid plan risk-free. Cancel anytime during the trial.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
