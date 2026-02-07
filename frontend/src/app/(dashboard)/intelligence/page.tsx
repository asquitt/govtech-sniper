"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { intelligenceApi } from "@/lib/api";
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
  const [loading, setLoading] = useState(true);
  const [kpis, setKpis] = useState<KPIData | null>(null);
  const [winLoss, setWinLoss] = useState<WinLossAnalysis | null>(null);
  const [budget, setBudget] = useState<BudgetIntelligenceData | null>(null);
  const [forecast, setForecast] = useState<PipelineForecast | null>(null);
  const [resources, setResources] = useState<ResourceAllocation | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [k, wl, b, f, r] = await Promise.all([
        intelligenceApi.getKPIs(),
        intelligenceApi.getWinLossAnalysis(),
        intelligenceApi.getBudgetIntelligence(),
        intelligenceApi.getPipelineForecast("quarterly"),
        intelligenceApi.getResourceAllocation(),
      ]);
      setKpis(k);
      setWinLoss(wl);
      setBudget(b);
      setForecast(f);
      setResources(r);
    } catch (err) {
      console.error("Failed to load intelligence data:", err);
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
