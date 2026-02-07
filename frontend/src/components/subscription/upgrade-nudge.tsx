"use client";

import React from "react";
import Link from "next/link";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

interface UpgradeNudgeProps {
  feature: string;
  requiredTier: string;
}

export function UpgradeNudge({ feature, requiredTier }: UpgradeNudgeProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3">
      <Sparkles className="h-5 w-5 text-primary flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground">
          {feature} requires the {requiredTier} plan
        </p>
        <p className="text-xs text-muted-foreground mt-0.5">
          Upgrade to unlock this feature and more.
        </p>
      </div>
      <Button size="sm" asChild>
        <Link href="/settings/subscription">Upgrade</Link>
      </Button>
    </div>
  );
}
