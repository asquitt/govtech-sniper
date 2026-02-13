"use client";

import React, { useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { dataSourcesApi } from "@/lib/api";
import { useAsyncData } from "@/hooks/use-async-data";
import type {
  DataSourceProvider,
  DataSourceSearchParams,
  DataSourceSearchResponse,
  DataSourceIngestResponse,
} from "@/types/data-sources";
import { IngestSummary, SearchResults } from "./_components/search-results";

export default function DataSourcesPage() {
  const { data: providers, error: fetchError, refetch } = useAsyncData<DataSourceProvider[]>(
    () => dataSourcesApi.listProviders(),
    [],
  );
  const [healthMap, setHealthMap] = useState<Record<string, boolean | null>>({});
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<DataSourceSearchResponse | null>(null);
  const [ingestResult, setIngestResult] = useState<DataSourceIngestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Search form state
  const [keywords, setKeywords] = useState("");
  const [agency, setAgency] = useState("");
  const [naicsCodes, setNaicsCodes] = useState("");
  const [daysBack, setDaysBack] = useState("90");
  const [limit, setLimit] = useState("25");

  const error = fetchError ? fetchError.message : actionError;

  const handleHealthCheck = async (providerName: string) => {
    setHealthMap((prev) => ({ ...prev, [providerName]: null }));
    try {
      const result = await dataSourcesApi.checkHealth(providerName);
      setHealthMap((prev) => ({ ...prev, [providerName]: result.healthy }));
    } catch {
      setHealthMap((prev) => ({ ...prev, [providerName]: false }));
    }
  };

  const buildSearchParams = (): DataSourceSearchParams => ({
    keywords: keywords.trim() || undefined,
    agency: agency.trim() || undefined,
    naics_codes: naicsCodes.trim()
      ? naicsCodes.split(",").map((c) => c.trim())
      : undefined,
    days_back: parseInt(daysBack, 10) || 90,
    limit: parseInt(limit, 10) || 25,
  });

  const handleSearch = async () => {
    if (!selectedProvider) return;
    setLoading(true);
    setActionError(null);
    setSearchResults(null);
    setIngestResult(null);
    try {
      const result = await dataSourcesApi.searchProvider(
        selectedProvider,
        buildSearchParams()
      );
      setSearchResults(result);
    } catch (err) {
      console.error("Search failed", err);
      setActionError("Search failed. Check provider configuration.");
    } finally {
      setLoading(false);
    }
  };

  const handleIngest = async () => {
    if (!selectedProvider) return;
    setLoading(true);
    setActionError(null);
    setIngestResult(null);
    try {
      const result = await dataSourcesApi.ingestFromProvider(
        selectedProvider,
        buildSearchParams()
      );
      setIngestResult(result);
    } catch (err) {
      console.error("Ingest failed", err);
      setActionError("Ingest failed. Check provider configuration.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Data Sources"
        description="Configure and search procurement data providers"
      />

      <div className="flex-1 p-6 overflow-auto space-y-6">
        {error && <p className="text-destructive text-sm">{error}</p>}

        {/* Provider Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(providers ?? []).map((p) => {
            const health = healthMap[p.provider_name];
            const isSelected = selectedProvider === p.provider_name;
            return (
              <Card
                key={p.provider_name}
                className={`border cursor-pointer transition-colors ${
                  isSelected
                    ? "border-primary ring-1 ring-primary"
                    : "border-border hover:border-muted-foreground"
                } ${!p.is_active ? "opacity-60" : ""}`}
                onClick={() =>
                  p.is_active && setSelectedProvider(p.provider_name)
                }
              >
                <CardContent className="p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-foreground">
                      {p.display_name}
                    </p>
                    <div className="flex items-center gap-2">
                      {health === true && (
                        <span className="h-2 w-2 rounded-full bg-green-500" />
                      )}
                      {health === false && (
                        <span className="h-2 w-2 rounded-full bg-red-500" />
                      )}
                      {health === null && (
                        <div className="h-2 w-2 rounded-full bg-muted-foreground animate-pulse" />
                      )}
                      <Badge variant={p.is_active ? "success" : "outline"}>
                        {p.is_active ? "Active" : "Coming Soon"}
                      </Badge>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {p.description}
                  </p>
                  {p.is_active && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleHealthCheck(p.provider_name);
                      }}
                    >
                      Check Health
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Search Form */}
        {selectedProvider && (
          <Card className="border border-border">
            <CardContent className="p-4 space-y-4">
              <p className="text-sm font-medium">
                Search:{" "}
                {(providers ?? []).find((p) => p.provider_name === selectedProvider)?.display_name}
              </p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <input
                  className="rounded-md border border-border bg-background px-3 py-2 text-sm"
                  placeholder="Keywords"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                />
                <input
                  className="rounded-md border border-border bg-background px-3 py-2 text-sm"
                  placeholder="Agency"
                  value={agency}
                  onChange={(e) => setAgency(e.target.value)}
                />
                <input
                  className="rounded-md border border-border bg-background px-3 py-2 text-sm"
                  placeholder="NAICS codes (comma-separated)"
                  value={naicsCodes}
                  onChange={(e) => setNaicsCodes(e.target.value)}
                />
                <input
                  className="rounded-md border border-border bg-background px-3 py-2 text-sm"
                  placeholder="Days back"
                  type="number"
                  value={daysBack}
                  onChange={(e) => setDaysBack(e.target.value)}
                />
                <input
                  className="rounded-md border border-border bg-background px-3 py-2 text-sm"
                  placeholder="Limit"
                  type="number"
                  value={limit}
                  onChange={(e) => setLimit(e.target.value)}
                />
              </div>
              <div className="flex gap-3">
                <Button onClick={handleSearch} disabled={loading}>
                  {loading ? "Searching..." : "Search"}
                </Button>
                <Button variant="outline" onClick={handleIngest} disabled={loading}>
                  {loading ? "Ingesting..." : "Search & Ingest"}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {ingestResult && <IngestSummary ingestResult={ingestResult} />}
        {searchResults && <SearchResults searchResults={searchResults} />}
      </div>
    </div>
  );
}
