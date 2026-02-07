"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Check, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PlanDefinition } from "@/types";

interface PlanCardProps {
  plan: PlanDefinition;
  currentTier: string;
  annual: boolean;
  onSelect: (tier: string) => void;
}

function formatPrice(cents: number): string {
  if (cents === 0) return "Free";
  return `$${(cents / 100).toFixed(0)}`;
}

export function PlanCard({ plan, currentTier, annual, onSelect }: PlanCardProps) {
  const isCurrent = plan.tier === currentTier;
  const price = annual ? plan.price_yearly : plan.price_monthly;
  const period = annual ? "/yr" : "/mo";

  return (
    <Card
      className={cn(
        "border relative",
        isCurrent
          ? "border-primary ring-2 ring-primary/20"
          : "border-border hover:border-primary/40 transition-colors"
      )}
    >
      {isCurrent && (
        <Badge className="absolute -top-2.5 left-4" variant="default">
          Current Plan
        </Badge>
      )}
      <CardContent className="p-5 space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-foreground">{plan.label}</h3>
          <p className="text-sm text-muted-foreground mt-1">{plan.description}</p>
        </div>

        <div className="flex items-baseline gap-1">
          <span className="text-3xl font-bold text-foreground">
            {formatPrice(price)}
          </span>
          {price > 0 && (
            <span className="text-sm text-muted-foreground">{period}</span>
          )}
        </div>

        <ul className="space-y-2">
          {plan.features.map((feature) => (
            <li key={feature.name} className="flex items-center gap-2 text-sm">
              {feature.included ? (
                <Check className="h-4 w-4 text-accent flex-shrink-0" />
              ) : (
                <X className="h-4 w-4 text-muted-foreground/50 flex-shrink-0" />
              )}
              <span
                className={cn(
                  feature.included
                    ? "text-foreground"
                    : "text-muted-foreground/60"
                )}
              >
                {feature.name}
              </span>
            </li>
          ))}
        </ul>

        <Button
          className="w-full"
          variant={isCurrent ? "outline" : "default"}
          disabled={isCurrent}
          onClick={() => onSelect(plan.tier)}
        >
          {isCurrent ? "Current Plan" : price === 0 ? "Downgrade" : "Upgrade"}
        </Button>
      </CardContent>
    </Card>
  );
}
