"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { forecastApi } from "@/lib/api";
import type { ProcurementForecast, ForecastAlert } from "@/types";

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export default function ForecastsPage() {
  const [forecasts, setForecasts] = useState<ProcurementForecast[]>([]);
  const [alerts, setAlerts] = useState<ForecastAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [title, setTitle] = useState("");
  const [agency, setAgency] = useState("");
  const [naics, setNaics] = useState("");
  const [value, setValue] = useState("");
  const [showForm, setShowForm] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [forecastList, alertList] = await Promise.all([
        forecastApi.list(),
        forecastApi.listAlerts(),
      ]);
      setForecasts(forecastList);
      setAlerts(alertList);
    } catch {
      setError("Failed to load forecast data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreate = async () => {
    if (!title.trim()) return;
    try {
      await forecastApi.create({
        title: title.trim(),
        agency: agency || undefined,
        naics_code: naics || undefined,
        estimated_value: value ? parseFloat(value) : undefined,
      });
      setTitle("");
      setAgency("");
      setNaics("");
      setValue("");
      setShowForm(false);
      fetchData();
    } catch {
      setError("Failed to create forecast.");
    }
  };

  const handleMatch = async () => {
    try {
      const result = await forecastApi.runMatching();
      fetchData();
      if (result.new_alerts === 0) {
        setError("No new matches found.");
      }
    } catch {
      setError("Failed to run matching.");
    }
  };

  const handleDismiss = async (alertId: number) => {
    try {
      await forecastApi.dismissAlert(alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch {
      setError("Failed to dismiss alert.");
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Procurement Forecasts"
        description="Track anticipated solicitations and match to existing opportunities"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleMatch}>
              Run Matching
            </Button>
            <Button size="sm" onClick={() => setShowForm(!showForm)}>
              {showForm ? "Cancel" : "Add Forecast"}
            </Button>
          </div>
        }
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {error && (
          <div className="bg-destructive/10 text-destructive rounded-lg p-4 flex items-center justify-between">
            <span>{error}</span>
            <Button variant="ghost" size="sm" onClick={() => setError(null)}>
              Dismiss
            </Button>
          </div>
        )}

        {/* Alerts */}
        {alerts.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>
                Forecast Alerts <Badge variant="secondary">{alerts.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {alerts.map((alert) => (
                <div key={alert.id} className="flex items-center justify-between text-sm border rounded-lg p-3">
                  <div>
                    <p className="font-medium">{alert.forecast_title}</p>
                    <p className="text-xs text-muted-foreground">
                      Matches: {alert.rfp_title}
                    </p>
                    <p className="text-xs text-muted-foreground">{alert.match_reason}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{Math.round(alert.match_score)}%</Badge>
                    <Button variant="ghost" size="sm" onClick={() => handleDismiss(alert.id)}>
                      Dismiss
                    </Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Create form */}
        {showForm && (
          <Card>
            <CardHeader>
              <CardTitle>New Forecast</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm bg-background"
                placeholder="Title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <div className="grid grid-cols-3 gap-3">
                <input
                  className="border rounded-lg px-3 py-2 text-sm bg-background"
                  placeholder="Agency"
                  value={agency}
                  onChange={(e) => setAgency(e.target.value)}
                />
                <input
                  className="border rounded-lg px-3 py-2 text-sm bg-background"
                  placeholder="NAICS Code"
                  value={naics}
                  onChange={(e) => setNaics(e.target.value)}
                />
                <input
                  className="border rounded-lg px-3 py-2 text-sm bg-background"
                  placeholder="Est. Value ($)"
                  type="number"
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                />
              </div>
              <Button size="sm" onClick={handleCreate}>
                Create Forecast
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Forecasts list */}
        <Card>
          <CardHeader>
            <CardTitle>Forecasts ({forecasts.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="animate-pulse space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-muted rounded" />
                ))}
              </div>
            ) : forecasts.length === 0 ? (
              <p className="text-muted-foreground text-sm text-center py-8">
                No forecasts yet. Add forecasts to track anticipated solicitations.
              </p>
            ) : (
              <div className="space-y-3">
                {forecasts.map((f) => (
                  <div key={f.id} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium">{f.title}</p>
                        <div className="flex gap-2 mt-1 text-xs text-muted-foreground">
                          {f.agency && <span>{f.agency}</span>}
                          {f.naics_code && <span>NAICS: {f.naics_code}</span>}
                          {f.fiscal_year && <span>FY{f.fiscal_year}</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {f.estimated_value && (
                          <span className="text-sm font-medium">
                            {formatCurrency(f.estimated_value)}
                          </span>
                        )}
                        <Badge variant={f.linked_rfp_id ? "default" : "outline"}>
                          {f.linked_rfp_id ? "Linked" : f.source}
                        </Badge>
                      </div>
                    </div>
                    {f.description && (
                      <p className="text-xs text-muted-foreground mt-2">{f.description}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
