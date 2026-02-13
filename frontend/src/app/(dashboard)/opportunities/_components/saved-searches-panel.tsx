"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate } from "@/lib/utils";
import { savedSearchApi } from "@/lib/api";
import type { RFPStatus, SavedSearch } from "@/types";
import { statusConfig } from "./opportunity-badges";

interface SavedSearchesPanelProps {
  savedSearches: SavedSearch[];
  activeSearchId: number | null;
  onSearchRun: (searchId: number, matchIds: number[]) => void;
  onSearchClear: () => void;
  onSearchesUpdated: (searches: SavedSearch[]) => void;
  onError: (message: string) => void;
}

export function SavedSearchesPanel({
  savedSearches,
  activeSearchId,
  onSearchRun,
  onSearchClear,
  onSearchesUpdated,
  onError,
}: SavedSearchesPanelProps) {
  const [name, setName] = useState("");
  const [keywords, setKeywords] = useState("");
  const [agencies, setAgencies] = useState("");
  const [naics, setNaics] = useState("");
  const [setAside, setSetAside] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [minValue, setMinValue] = useState("");
  const [maxValue, setMaxValue] = useState("");
  const [status, setStatus] = useState<RFPStatus | "">("");

  const handleCreate = async () => {
    if (!name.trim()) return;
    try {
      const filters: Record<string, unknown> = {
        keywords: keywords.split(",").map((s) => s.trim()).filter(Boolean),
        agencies: agencies.split(",").map((s) => s.trim()).filter(Boolean),
        naics_codes: naics.split(",").map((s) => s.trim()).filter(Boolean),
        set_asides: setAside.split(",").map((s) => s.trim()).filter(Boolean),
        source_types: sourceType.split(",").map((s) => s.trim()).filter(Boolean),
        statuses: status ? [status] : [],
      };

      if (minValue) {
        const min = Number(minValue);
        if (!Number.isNaN(min)) filters.min_value = min;
      }
      if (maxValue) {
        const max = Number(maxValue);
        if (!Number.isNaN(max)) filters.max_value = max;
      }

      await savedSearchApi.create({ name: name.trim(), filters });

      setName("");
      setKeywords("");
      setAgencies("");
      setNaics("");
      setSetAside("");
      setSourceType("");
      setMinValue("");
      setMaxValue("");
      setStatus("");

      const savedSearchList = await savedSearchApi.list();
      onSearchesUpdated(savedSearchList);
    } catch (err) {
      console.error("Failed to create saved search", err);
      onError("Failed to create saved search.");
    }
  };

  const handleRun = async (searchId: number) => {
    try {
      const result = await savedSearchApi.run(searchId);
      onSearchRun(searchId, result.matches.map((m) => m.id));
    } catch (err) {
      console.error("Failed to run saved search", err);
      onError("Failed to run saved search.");
    }
  };

  return (
    <Card className="border border-border mb-6">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Saved Searches</p>
            <p className="text-xs text-muted-foreground">
              Reuse filters for federal and SLED opportunities.
            </p>
          </div>
          {activeSearchId !== null && (
            <Button variant="outline" size="sm" onClick={onSearchClear}>
              Clear Active Search
            </Button>
          )}
        </div>

        <div className="grid grid-cols-3 gap-3">
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Search name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Keywords (comma-separated)"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Agencies (comma-separated)"
            value={agencies}
            onChange={(e) => setAgencies(e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="NAICS codes"
            value={naics}
            onChange={(e) => setNaics(e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Set-Asides"
            value={setAside}
            onChange={(e) => setSetAside(e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Source Type (federal, sled)"
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Min Value"
            value={minValue}
            onChange={(e) => setMinValue(e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Max Value"
            value={maxValue}
            onChange={(e) => setMaxValue(e.target.value)}
          />
          <select
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            value={status}
            onChange={(e) => setStatus(e.target.value as RFPStatus | "")}
          >
            <option value="">Any Status</option>
            {Object.keys(statusConfig).map((s) => (
              <option key={s} value={s}>
                {statusConfig[s as RFPStatus].label}
              </option>
            ))}
          </select>
        </div>

        <Button onClick={handleCreate} size="sm">
          Save Search
        </Button>

        {savedSearches.length === 0 ? (
          <p className="text-sm text-muted-foreground">No saved searches yet.</p>
        ) : (
          <div className="space-y-2">
            {savedSearches.map((search) => (
              <div
                key={search.id}
                className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
              >
                <div>
                  <p className="font-medium text-foreground">{search.name}</p>
                  <p className="text-xs text-muted-foreground">
                    Last run: {search.last_run_at ? formatDate(search.last_run_at) : "\u2014"} ·
                    Matches: {search.last_match_count}
                  </p>
                </div>
                <Button
                  variant={activeSearchId === search.id ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleRun(search.id)}
                >
                  {activeSearchId === search.id ? "Active" : "Run"}
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
