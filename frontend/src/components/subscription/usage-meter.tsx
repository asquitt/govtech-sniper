"use client";

import React from "react";
import { Progress } from "@/components/ui/progress";
import type { UsageStats } from "@/types";

interface UsageMeterProps {
  usage: UsageStats;
}

interface MeterRowProps {
  label: string;
  used: number;
  limit: number;
}

function MeterRow({ label, used, limit }: MeterRowProps) {
  const unlimited = limit < 0;
  const percent = unlimited ? 0 : limit === 0 ? 100 : Math.min((used / limit) * 100, 100);
  const isWarning = !unlimited && percent >= 80;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium text-foreground">
          {used.toLocaleString()}{" "}
          <span className="text-muted-foreground font-normal">
            / {unlimited ? "Unlimited" : limit.toLocaleString()}
          </span>
        </span>
      </div>
      {!unlimited && (
        <Progress
          value={percent}
          className={isWarning ? "[&>div]:bg-warning" : ""}
        />
      )}
    </div>
  );
}

export function UsageMeter({ usage }: UsageMeterProps) {
  return (
    <div className="space-y-4">
      <MeterRow label="RFPs tracked" used={usage.rfps_used} limit={usage.rfps_limit} />
      <MeterRow label="Proposals" used={usage.proposals_used} limit={usage.proposals_limit} />
      <MeterRow label="API calls today" used={usage.api_calls_used} limit={usage.api_calls_limit} />
    </div>
  );
}
