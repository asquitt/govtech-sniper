"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ConversionRatesData } from "@/types";

interface ConversionFunnelProps {
  data: ConversionRatesData | null;
  loading: boolean;
}

const STAGE_LABELS: Record<string, string> = {
  identified: "Identified",
  qualified: "Qualified",
  pursuit: "Pursuit",
  proposal: "Proposal",
  submitted: "Submitted",
  won: "Won",
};

export function ConversionFunnel({ data, loading }: ConversionFunnelProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Conversion Funnel</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-8 bg-muted rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const conversions = data?.conversions ?? [];
  const overallRate = data?.overall_rate ?? 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">Conversion Funnel</CardTitle>
        <span className="text-xs text-muted-foreground">
          Overall: {overallRate}%
        </span>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {conversions.map((c) => (
            <div key={`${c.from_stage}-${c.to_stage}`}>
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-muted-foreground">
                  {STAGE_LABELS[c.from_stage] ?? c.from_stage}{" "}
                  <span className="text-foreground/40">&rarr;</span>{" "}
                  {STAGE_LABELS[c.to_stage] ?? c.to_stage}
                </span>
                <span className="font-medium">{c.rate}%</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all"
                  style={{ width: `${Math.min(c.rate, 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-muted-foreground mt-0.5">
                <span>{c.count_from} entered</span>
                <span>{c.count_to} progressed</span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
