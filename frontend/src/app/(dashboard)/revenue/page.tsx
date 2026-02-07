"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { revenueApi } from "@/lib/api";
import type {
  PipelineSummaryResponse,
  RevenueTimelineResponse,
  AgencyRevenueResponse,
} from "@/types";
import { PipelineSummaryCards } from "@/components/revenue/pipeline-summary-cards";
import { RevenueTimelineChart } from "@/components/revenue/revenue-timeline-chart";
import { AgencyBreakdownChart } from "@/components/revenue/agency-breakdown-chart";

export default function RevenuePage() {
  const [summary, setSummary] = useState<PipelineSummaryResponse | null>(null);
  const [timeline, setTimeline] = useState<RevenueTimelineResponse | null>(null);
  const [agencyData, setAgencyData] = useState<AgencyRevenueResponse | null>(null);
  const [granularity, setGranularity] = useState<"monthly" | "quarterly">("monthly");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, timelineRes, agencyRes] = await Promise.all([
        revenueApi.getPipelineSummary(),
        revenueApi.getTimeline(granularity),
        revenueApi.getByAgency(),
      ]);
      setSummary(summaryRes);
      setTimeline(timelineRes);
      setAgencyData(agencyRes);
    } catch {
      setError("Failed to load revenue data. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [granularity]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Revenue Forecasting"
        description="Pipeline value analysis weighted by win probability"
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

        <PipelineSummaryCards data={summary} loading={loading} />

        <div className="flex gap-2">
          <Button
            variant={granularity === "monthly" ? "default" : "outline"}
            size="sm"
            onClick={() => setGranularity("monthly")}
          >
            Monthly
          </Button>
          <Button
            variant={granularity === "quarterly" ? "default" : "outline"}
            size="sm"
            onClick={() => setGranularity("quarterly")}
          >
            Quarterly
          </Button>
        </div>

        <RevenueTimelineChart data={timeline} loading={loading} />

        <AgencyBreakdownChart data={agencyData} loading={loading} />
      </div>
    </div>
  );
}
