"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { GanttPlanRow } from "@/types";

const STATUS_COLORS: Record<string, string> = {
  planned: "hsl(var(--primary))",
  in_progress: "hsl(45, 93%, 47%)",
  completed: "hsl(142, 71%, 45%)",
  overdue: "hsl(0, 84%, 60%)",
};

const STAGE_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  identified: "outline",
  qualified: "secondary",
  pursuit: "secondary",
  proposal: "default",
  submitted: "default",
  won: "default",
  lost: "destructive",
};

interface GanttChartProps {
  data: GanttPlanRow[];
  loading: boolean;
}

export function GanttChart({ data, loading }: GanttChartProps) {
  const chartData = useMemo(() => {
    if (!data.length) return [];

    // Find global date range
    let minDate = Infinity;
    let maxDate = -Infinity;
    for (const row of data) {
      for (const act of row.activities) {
        if (act.start_date) {
          const t = new Date(act.start_date).getTime();
          if (t < minDate) minDate = t;
        }
        if (act.end_date) {
          const t = new Date(act.end_date).getTime();
          if (t > maxDate) maxDate = t;
        }
      }
      if (row.response_deadline) {
        const t = new Date(row.response_deadline).getTime();
        if (t > maxDate) maxDate = t;
      }
    }

    if (!isFinite(minDate)) return [];

    const totalSpan = maxDate - minDate || 1;

    return data.flatMap((row) =>
      row.activities.map((act) => {
        const start = act.start_date
          ? ((new Date(act.start_date).getTime() - minDate) / totalSpan) * 100
          : 0;
        const end = act.end_date
          ? ((new Date(act.end_date).getTime() - minDate) / totalSpan) * 100
          : start + 5;
        return {
          label: `${row.rfp_title.slice(0, 25)} — ${act.title}`,
          start,
          duration: Math.max(end - start, 2),
          status: act.status,
          milestone: act.is_milestone,
          rfpTitle: row.rfp_title,
          actTitle: act.title,
          startDate: act.start_date,
          endDate: act.end_date,
        };
      })
    );
  }, [data]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Gantt View</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px] animate-pulse bg-muted rounded" />
        </CardContent>
      </Card>
    );
  }

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Gantt View</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            No activities yet. Add activities to your capture plans to see the timeline.
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Gantt View</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 36)}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 20, left: 200, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={false} />
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis
              type="category"
              dataKey="label"
              className="text-xs"
              width={190}
              tick={{ fontSize: 11 }}
            />
            <Tooltip
              content={({ payload }) => {
                if (!payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-popover border rounded-lg p-3 shadow-md text-sm">
                    <p className="font-semibold">{d.actTitle}</p>
                    <p className="text-muted-foreground text-xs">{d.rfpTitle}</p>
                    <p className="mt-1">
                      {d.startDate ?? "TBD"} → {d.endDate ?? "TBD"}
                    </p>
                    <Badge variant="outline" className="mt-1">
                      {d.status}
                    </Badge>
                  </div>
                );
              }}
            />
            {/* Invisible offset bar */}
            <Bar dataKey="start" stackId="gantt" fill="transparent" />
            <Bar dataKey="duration" stackId="gantt" radius={[4, 4, 4, 4]}>
              {chartData.map((entry, idx) => (
                <Cell
                  key={idx}
                  fill={STATUS_COLORS[entry.status] ?? STATUS_COLORS.planned}
                  stroke={entry.milestone ? "#000" : "none"}
                  strokeWidth={entry.milestone ? 2 : 0}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        <div className="flex gap-4 mt-4 text-xs">
          {Object.entries(STATUS_COLORS).map(([status, color]) => (
            <div key={status} className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: color }} />
              <span className="capitalize">{status.replace("_", " ")}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export { STAGE_VARIANT };
