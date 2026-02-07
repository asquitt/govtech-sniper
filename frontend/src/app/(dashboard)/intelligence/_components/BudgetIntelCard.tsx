"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { BudgetIntelligenceData } from "@/types";

interface BudgetIntelCardProps {
  data: BudgetIntelligenceData | null;
  loading: boolean;
}

const MONTH_NAMES = [
  "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function formatCurrency(value: number): string {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export function BudgetIntelCard({ data, loading }: BudgetIntelCardProps) {
  if (loading || !data) {
    return (
      <Card className="border border-border">
        <CardContent className="p-5">
          <div className="animate-pulse space-y-3">
            <div className="h-5 w-40 bg-muted rounded" />
            <div className="h-48 bg-muted rounded" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const maxRfpCount = Math.max(...data.budget_season.map((s) => s.rfp_count), 1);

  return (
    <Card className="border border-border">
      <CardContent className="p-5 space-y-5">
        <p className="text-sm font-medium text-foreground">Budget Intelligence</p>

        {/* Budget Season Heatmap */}
        {data.budget_season.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-2">
              RFP Activity by Month (Budget Season)
            </p>
            <div className="flex gap-1">
              {Array.from({ length: 12 }, (_, i) => {
                const monthData = data.budget_season.find((s) => s.month === i + 1);
                const count = monthData?.rfp_count ?? 0;
                const intensity = count / maxRfpCount;
                return (
                  <div key={i} className="flex-1 text-center">
                    <div
                      className="h-8 rounded-sm mb-1"
                      style={{
                        backgroundColor: `rgba(59, 130, 246, ${Math.max(intensity * 0.8, 0.05)})`,
                      }}
                      title={`${MONTH_NAMES[i + 1]}: ${count} RFPs`}
                    />
                    <span className="text-[9px] text-muted-foreground">
                      {MONTH_NAMES[i + 1]}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Top Agencies by Spend */}
        {data.top_agencies.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-2">Top Agencies by Spend</p>
            <div className="space-y-1.5">
              {data.top_agencies.slice(0, 8).map((a) => (
                <div key={a.agency} className="flex items-center justify-between text-sm">
                  <span className="text-foreground truncate max-w-[220px]">{a.agency}</span>
                  <span className="text-xs font-medium text-foreground">
                    {formatCurrency(a.total_spend)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top NAICS */}
        {data.top_naics.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-2">
              Top NAICS Codes by Spend
            </p>
            <div className="space-y-1.5">
              {data.top_naics.slice(0, 6).map((n) => (
                <div key={n.naics_code} className="flex items-center justify-between text-sm">
                  <Badge variant="outline" className="text-[10px]">
                    {n.naics_code}
                  </Badge>
                  <span className="text-xs font-medium text-foreground">
                    {formatCurrency(n.total_spend)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top Competitors */}
        {data.top_competitors.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-2">
              Top Competitors by Award Value
            </p>
            <div className="space-y-1.5">
              {data.top_competitors.slice(0, 8).map((c) => (
                <div key={c.vendor} className="flex items-center justify-between text-sm">
                  <span className="text-foreground truncate max-w-[200px]">{c.vendor}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">{c.wins} wins</span>
                    <span className="text-xs font-medium">{formatCurrency(c.total_value)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {data.top_agencies.length === 0 && data.top_competitors.length === 0 && (
          <div className="text-center py-6 text-muted-foreground">
            <p className="text-sm">No budget intelligence data yet</p>
            <p className="text-xs mt-1">
              Import award records to see spending trends
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
