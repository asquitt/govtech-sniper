"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { PipelineByStageData } from "@/types";

interface PipelineChartProps {
  data: PipelineByStageData | null;
  loading: boolean;
}

const STAGE_LABELS: Record<string, string> = {
  identified: "Identified",
  qualified: "Qualified",
  pursuit: "Pursuit",
  proposal: "Proposal",
  submitted: "Submitted",
  won: "Won",
  lost: "Lost",
};

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value}`;
}

export function PipelineChart({ data, loading }: PipelineChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Pipeline by Stage</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse h-64 bg-muted rounded" />
        </CardContent>
      </Card>
    );
  }

  const chartData = (data?.stages ?? []).map((s) => ({
    ...s,
    label: STAGE_LABELS[s.stage] ?? s.stage,
  }));

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">Pipeline by Stage</CardTitle>
        <span className="text-xs text-muted-foreground">
          Total: {formatCurrency(data?.total_pipeline_value ?? 0)}
        </span>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                type="number"
                tickFormatter={formatCurrency}
                className="text-xs"
              />
              <YAxis
                dataKey="label"
                type="category"
                width={80}
                className="text-xs"
              />
              <Tooltip
                formatter={(value: number | undefined) => [formatCurrency(value ?? 0), "Value"]}
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                }}
              />
              <Bar
                dataKey="total_value"
                fill="hsl(var(--primary))"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
