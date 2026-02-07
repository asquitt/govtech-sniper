"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { captureTimelineApi } from "@/lib/api";
import type { GanttPlanRow } from "@/types";
import { GanttChart, STAGE_VARIANT } from "@/components/pipeline/gantt-chart";
import { DeadlineAlerts } from "@/components/pipeline/deadline-alerts";

export default function PipelinePage() {
  const [rows, setRows] = useState<GanttPlanRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await captureTimelineApi.getOverview();
      setRows(data);
    } catch {
      setError("Failed to load pipeline data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Pipeline Timeline"
        description="Gantt view of capture plan activities and deadlines"
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {error && (
          <div className="bg-destructive/10 text-destructive rounded-lg p-4 flex items-center justify-between">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={fetchData}>
              Retry
            </Button>
          </div>
        )}

        {/* Stage summary badges */}
        {!loading && rows.length > 0 && (
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

        <DeadlineAlerts data={rows} />

        <GanttChart data={rows} loading={loading} />
      </div>
    </div>
  );
}
