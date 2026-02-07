"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import type { PipelineForecast } from "@/types";

interface ForecastCardProps {
  data: PipelineForecast | null;
  loading: boolean;
}

function formatCurrency(value: number): string {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export function ForecastCard({ data, loading }: ForecastCardProps) {
  if (loading || !data) {
    return (
      <Card className="border border-border">
        <CardContent className="p-5">
          <div className="animate-pulse space-y-3">
            <div className="h-5 w-40 bg-muted rounded" />
            <div className="h-40 bg-muted rounded" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const maxValue = Math.max(
    ...data.forecast.map((f) => f.optimistic_value),
    1
  );

  return (
    <Card className="border border-border">
      <CardContent className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-foreground">Pipeline Forecast</p>
          <div className="flex gap-3 text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-500" /> Weighted
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-300" /> Optimistic
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-200" /> Pessimistic
            </span>
          </div>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Weighted Total</p>
            <p className="text-lg font-bold text-foreground">
              {formatCurrency(data.total_weighted)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Unweighted Total</p>
            <p className="text-lg font-bold text-muted-foreground">
              {formatCurrency(data.total_unweighted)}
            </p>
          </div>
        </div>

        {/* Bar Chart */}
        {data.forecast.length > 0 ? (
          <div className="space-y-2">
            {data.forecast.map((f) => {
              const weightedPct = (f.weighted_value / maxValue) * 100;
              const optimisticPct = (f.optimistic_value / maxValue) * 100;
              const pessimisticPct = (f.pessimistic_value / maxValue) * 100;

              return (
                <div key={f.period} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground font-medium">
                      {f.period}
                    </span>
                    <span className="text-foreground font-medium">
                      {formatCurrency(f.weighted_value)}
                    </span>
                  </div>
                  <div className="relative h-5 bg-muted/50 rounded overflow-hidden">
                    <div
                      className="absolute inset-y-0 left-0 bg-blue-200/40 rounded"
                      style={{ width: `${optimisticPct}%` }}
                    />
                    <div
                      className="absolute inset-y-0 left-0 bg-blue-300/50 rounded"
                      style={{ width: `${weightedPct}%` }}
                    />
                    <div
                      className="absolute inset-y-0 left-0 bg-blue-500 rounded"
                      style={{ width: `${pessimisticPct}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-muted-foreground">
                    <span>{f.opportunity_count} opps</span>
                    <span>
                      {formatCurrency(f.pessimistic_value)} –{" "}
                      {formatCurrency(f.optimistic_value)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-6 text-muted-foreground">
            <p className="text-sm">No forecast data available</p>
            <p className="text-xs mt-1">
              Add opportunities with deadlines and win probabilities
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
