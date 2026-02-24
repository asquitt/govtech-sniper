"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { analyticsApi } from "@/lib/api";
import type {
  WinRateData,
  PipelineByStageData,
  ConversionRatesData,
  ProposalTurnaroundData,
  NAICSPerformanceData,
} from "@/types";
import { WinRateCard } from "./_components/WinRateCard";
import { PipelineChart } from "./_components/PipelineChart";
import { ConversionFunnel } from "./_components/ConversionFunnel";
import { TurnaroundChart } from "./_components/TurnaroundChart";
import { NaicsTable } from "./_components/NaicsTable";
import { ExportButton } from "./_components/ExportButton";

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [winRate, setWinRate] = useState<WinRateData | null>(null);
  const [pipeline, setPipeline] = useState<PipelineByStageData | null>(null);
  const [conversion, setConversion] = useState<ConversionRatesData | null>(null);
  const [turnaround, setTurnaround] = useState<ProposalTurnaroundData | null>(null);
  const [naics, setNaics] = useState<NAICSPerformanceData | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [wr, pl, cv, ta, nc] = await Promise.all([
        analyticsApi.getWinRate(),
        analyticsApi.getPipelineByStage(),
        analyticsApi.getConversionRates(),
        analyticsApi.getProposalTurnaround(),
        analyticsApi.getNaicsPerformance(),
      ]);
      setWinRate(wr);
      setPipeline(pl);
      setConversion(cv);
      setTurnaround(ta);
      setNaics(nc);
    } catch (err) {
      console.error("Failed to load analytics:", err);
      setError("Failed to load analytics data. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Analytics"
        description="Win rates, pipeline performance, and reporting"
        actions={<ExportButton />}
      />
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {error && (
          <div role="alert" className="rounded-md bg-destructive/10 p-4 text-sm text-destructive flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={fetchAll}
              className="ml-4 underline hover:no-underline"
              aria-label="Retry loading analytics"
            >
              Retry
            </button>
          </div>
        )}
        {/* KPI Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <WinRateCard data={winRate} loading={loading} />
          <div className="md:col-span-2">
            <PipelineChart data={pipeline} loading={loading} />
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ConversionFunnel data={conversion} loading={loading} />
          <TurnaroundChart data={turnaround} loading={loading} />
        </div>

        {/* NAICS Table */}
        <NaicsTable data={naics} loading={loading} />
      </div>
    </div>
  );
}
