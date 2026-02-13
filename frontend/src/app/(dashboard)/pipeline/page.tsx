"use client";

import React from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { captureTimelineApi } from "@/lib/api";
import type { GanttPlanRow } from "@/types";
import { GanttChart, STAGE_VARIANT } from "@/components/pipeline/gantt-chart";
import { DeadlineAlerts } from "@/components/pipeline/deadline-alerts";
import { useAsyncData } from "@/hooks/use-async-data";

export default function PipelinePage() {
  const { data: rows, loading, error, refetch } = useAsyncData<GanttPlanRow[]>(
    () => captureTimelineApi.getOverview(),
    [],
  );

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Pipeline Timeline"
        description="Gantt view of capture plan activities and deadlines"
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {error && (
          <div className="bg-destructive/10 text-destructive rounded-lg p-4 flex items-center justify-between">
            <span>{error.message}</span>
            <Button variant="outline" size="sm" onClick={refetch}>
              Retry
            </Button>
          </div>
        )}

        {/* Stage summary badges */}
        {!loading && rows && rows.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {Object.entries(
              rows.reduce<Record<string, number>>((acc, r) => {
                acc[r.stage] = (acc[r.stage] || 0) + 1;
                return acc;
              }, {})
            ).map(([stage, count]) => (
              <Badge
                key={stage}
                variant={STAGE_VARIANT[stage] ?? "outline"}
              >
                {stage}: {count}
              </Badge>
            ))}
          </div>
        )}

        <DeadlineAlerts data={rows ?? []} />

        <GanttChart data={rows ?? []} loading={loading} />
      </div>
    </div>
  );
}
