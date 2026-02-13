"use client";

import React from "react";
import { Header } from "@/components/layout/header";
import { intelligenceApi } from "@/lib/api";
import { useAsyncData } from "@/hooks/use-async-data";
import type {
  KPIData,
  WinLossAnalysis,
  BudgetIntelligenceData,
  PipelineForecast,
  ResourceAllocation,
} from "@/types";
import { KPICards } from "./_components/KPICards";
import { WinLossCard } from "./_components/WinLossCard";
import { BudgetIntelCard } from "./_components/BudgetIntelCard";
import { ForecastCard } from "./_components/ForecastCard";
import { ResourceCard } from "./_components/ResourceCard";

export default function IntelligencePage() {
  interface IntelligenceData {
    kpis: KPIData;
    winLoss: WinLossAnalysis;
    budget: BudgetIntelligenceData;
    forecast: PipelineForecast;
    resources: ResourceAllocation;
  }

  const { data, loading } = useAsyncData<IntelligenceData>(
    async () => {
      const [k, wl, b, f, r] = await Promise.all([
        intelligenceApi.getKPIs(),
        intelligenceApi.getWinLossAnalysis(),
        intelligenceApi.getBudgetIntelligence(),
        intelligenceApi.getPipelineForecast("quarterly"),
        intelligenceApi.getResourceAllocation(),
      ]);
      return { kpis: k, winLoss: wl, budget: b, forecast: f, resources: r };
    },
    [],
  );

  const kpis = data?.kpis ?? null;
  const winLoss = data?.winLoss ?? null;
  const budget = data?.budget ?? null;
  const forecast = data?.forecast ?? null;
  const resources = data?.resources ?? null;

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Intelligence"
        description="Market intelligence, win/loss analysis, and pipeline forecasting"
      />
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* KPI Cards Row */}
        <KPICards data={kpis} loading={loading} />

        {/* Main content: 2-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <WinLossCard data={winLoss} loading={loading} />
          <BudgetIntelCard data={budget} loading={loading} />
        </div>

        {/* Forecast + Resource Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ForecastCard data={forecast} loading={loading} />
          <ResourceCard data={resources} loading={loading} />
        </div>
      </div>
    </div>
  );
}
