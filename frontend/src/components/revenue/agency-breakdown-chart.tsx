"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AgencyRevenueResponse } from "@/types";

function formatAxisValue(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value}`;
}

interface AgencyBreakdownChartProps {
  data: AgencyRevenueResponse | null;
  loading: boolean;
}

export function AgencyBreakdownChart({ data, loading }: AgencyBreakdownChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Revenue by Agency</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px] animate-pulse bg-muted rounded" />
        </CardContent>
      </Card>
    );
  }

  const agencies = data?.agencies ?? [];

  if (agencies.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Revenue by Agency</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px] flex items-center justify-center text-muted-foreground">
            No agency data available. Add opportunities with agency and value information.
          </div>
        </CardContent>
      </Card>
    );
  }

  // Truncate long agency names for chart display
  const chartData = agencies.map((a) => ({
    ...a,
    agency: a.agency.length > 30 ? `${a.agency.slice(0, 27)}...` : a.agency,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Revenue by Agency</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={Math.max(300, agencies.length * 40)}>
          <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 20, left: 120, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis type="number" tickFormatter={formatAxisValue} className="text-xs" />
            <YAxis type="category" dataKey="agency" className="text-xs" width={110} />
            <Tooltip formatter={(value) => formatAxisValue(Number(value))} />
            <Legend />
            <Bar
              dataKey="weighted_value"
              name="Weighted Pipeline"
              fill="hsl(var(--primary))"
              radius={[0, 4, 4, 0]}
            />
            <Bar
              dataKey="won_value"
              name="Won Revenue"
              fill="hsl(142, 71%, 45%)"
              radius={[0, 4, 4, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
