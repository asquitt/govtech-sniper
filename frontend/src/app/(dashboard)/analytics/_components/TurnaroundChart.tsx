"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { ProposalTurnaroundData } from "@/types";

interface TurnaroundChartProps {
  data: ProposalTurnaroundData | null;
  loading: boolean;
}

export function TurnaroundChart({ data, loading }: TurnaroundChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Proposal Turnaround</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse h-64 bg-muted rounded" />
        </CardContent>
      </Card>
    );
  }

  const overallAvg = data?.overall_avg_days ?? 0;
  const trend = data?.trend ?? [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">Proposal Turnaround</CardTitle>
        <span className="text-xs text-muted-foreground">
          Avg: {overallAvg} days
        </span>
      </CardHeader>
      <CardContent>
        {trend.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">
            No turnaround data yet
          </div>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="month" className="text-xs" />
                <YAxis className="text-xs" unit=" d" />
                <Tooltip
                  formatter={(value: number | undefined) => [`${value ?? 0} days`, "Avg Turnaround"]}
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="avg_days"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
