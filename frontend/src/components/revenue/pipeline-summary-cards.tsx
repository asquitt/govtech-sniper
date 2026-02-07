"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { PipelineSummaryResponse } from "@/types";

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

interface PipelineSummaryCardsProps {
  data: PipelineSummaryResponse | null;
  loading: boolean;
}

export function PipelineSummaryCards({ data, loading }: PipelineSummaryCardsProps) {
  const cards = [
    {
      label: "Weighted Pipeline",
      value: data ? formatCurrency(data.total_weighted) : "--",
      sub: data ? `${data.total_opportunities} opportunities` : "",
    },
    {
      label: "Unweighted Pipeline",
      value: data ? formatCurrency(data.total_unweighted) : "--",
      sub: "Total estimated value",
    },
    {
      label: "Won Revenue",
      value: data ? formatCurrency(data.won_value) : "--",
      sub: "Active contracts",
    },
    {
      label: "Win Rate Value",
      value:
        data && data.total_unweighted > 0
          ? `${((data.total_weighted / data.total_unweighted) * 100).toFixed(0)}%`
          : "--",
      sub: "Avg win probability",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <Card key={card.label}>
          <CardContent className="pt-6">
            {loading ? (
              <div className="animate-pulse space-y-2">
                <div className="h-4 bg-muted rounded w-24" />
                <div className="h-8 bg-muted rounded w-32" />
              </div>
            ) : (
              <>
                <p className="text-sm text-muted-foreground">{card.label}</p>
                <p className="text-2xl font-bold mt-1">{card.value}</p>
                <p className="text-xs text-muted-foreground mt-1">{card.sub}</p>
              </>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
