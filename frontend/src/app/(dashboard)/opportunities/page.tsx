"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Search,
  Filter,
  Plus,
  AlertTriangle,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getApiErrorMessage } from "@/lib/api/error";
import { rfpApi, ingestApi, savedSearchApi } from "@/lib/api";
import type { RFPListItem, SavedSearch } from "@/types";
import { parseRetryAfterSeconds, formatSeconds } from "./_components/opportunity-badges";
import { StatsCards } from "./_components/stats-cards";
import { SavedSearchesPanel } from "./_components/saved-searches-panel";
import { CreateRfpForm } from "./_components/create-rfp-form";
import { OpportunitiesTable } from "./_components/opportunities-table";

export default function OpportunitiesPage() {
  const [rfps, setRfps] = useState<RFPListItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [showRecommended, setShowRecommended] = useState(false);
  const [syncCooldownSeconds, setSyncCooldownSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [activeSearchId, setActiveSearchId] = useState<number | null>(null);
  const [activeSearchMatchIds, setActiveSearchMatchIds] = useState<number[]>([]);
  const [showCreateRfp, setShowCreateRfp] = useState(false);
  const [stats, setStats] = useState({
    total: 0,
    qualified: 0,
    pending: 0,
    analyzing: 0,
  });

  const fetchRfps = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const [rfpList, rfpStats, savedSearchList] = await Promise.all([
        rfpApi.list(),
        rfpApi.getStats(),
        savedSearchApi.list(),
      ]);

      setRfps(rfpList);
      setSavedSearches(savedSearchList);
      setStats({
        total: rfpStats.total,
        qualified: rfpStats.qualified,
        pending: rfpStats.pending_filter,
        analyzing: rfpStats.by_status?.analyzing || 0,
      });
    } catch (err) {
      console.error("Failed to fetch RFPs:", err);
      setError("Failed to load opportunities. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRfps();
  }, [fetchRfps]);

  useEffect(() => {
    if (syncCooldownSeconds <= 0) return;

    const timer = window.setInterval(() => {
      setSyncCooldownSeconds((current) => Math.max(0, current - 1));
    }, 1000);

    return () => window.clearInterval(timer);
  }, [syncCooldownSeconds]);

  const handleSync = async () => {
    if (syncCooldownSeconds > 0) {
      setError(
        `SAM.gov sync is cooling down. Try again in ${formatSeconds(syncCooldownSeconds)}.`
      );
      return;
    }

    try {
      setIsSyncing(true);
      setError(null);
      const result = await ingestApi.triggerSamSearch({
        keywords: "software",
        days_back: 30,
        limit: 100,
      });

      if (result.status !== "completed" && result.status !== "failed") {
        let taskComplete = false;
        let attempts = 0;
        const maxAttempts = 60;
        while (!taskComplete && attempts < maxAttempts) {
          await new Promise((resolve) => setTimeout(resolve, 2000));
          const status = await ingestApi.getTaskStatus(result.task_id);
          if (status.status === "completed" || status.status === "failed") {
            taskComplete = true;
          }
          attempts += 1;
        }

        if (!taskComplete) {
          setError("Sync is taking longer than expected. Please refresh shortly.");
        }
      }

      await fetchRfps();
      setSyncCooldownSeconds(0);
    } catch (err) {
      console.error("SAM.gov sync failed:", err);
      const retryAfterSeconds = parseRetryAfterSeconds(err);
      if (retryAfterSeconds && retryAfterSeconds > 0) {
        setSyncCooldownSeconds(retryAfterSeconds);
      }
      setError(getApiErrorMessage(err, "Failed to sync with SAM.gov. Please try again."));
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSearchRun = (searchId: number, matchIds: number[]) => {
    setActiveSearchId(searchId);
    setActiveSearchMatchIds(matchIds);
  };

  const handleSearchClear = () => {
    setActiveSearchId(null);
    setActiveSearchMatchIds([]);
  };

  const activeMatchSet = useMemo(
    () => new Set(activeSearchMatchIds),
    [activeSearchMatchIds]
  );

  const filteredRfps = rfps.filter(
    (rfp) =>
      rfp.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rfp.solicitation_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rfp.agency?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const baseRfps =
    activeSearchId !== null
      ? filteredRfps.filter((rfp) => activeMatchSet.has(rfp.id))
      : filteredRfps;

  const recommendedOnly = baseRfps.filter(
    (rfp) =>
      (rfp.recommendation_score ?? 0) >= 70 &&
      (rfp.is_qualified ?? false)
  );
  const recommendedRfps = showRecommended
    ? (recommendedOnly.length > 0 ? recommendedOnly : baseRfps)
    : baseRfps;

  const sortedRfps = [...recommendedRfps].sort((a, b) => {
    const aScore = a.recommendation_score ?? 0;
    const bScore = b.recommendation_score ?? 0;
    if (aScore !== bScore) return bScore - aScore;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Opportunities"
        description="Track and manage government contract opportunities"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant={showRecommended ? "default" : "outline"}
              onClick={() => setShowRecommended((prev) => !prev)}
            >
              Recommended
            </Button>
            <Button onClick={handleSync} disabled={isSyncing || syncCooldownSeconds > 0}>
              {isSyncing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              {syncCooldownSeconds > 0
                ? `Sync in ${formatSeconds(syncCooldownSeconds)}`
                : "Sync SAM.gov"}
            </Button>
          </div>
        }
      />

      <div className="flex-1 p-6 overflow-hidden">
        {error && (
          <Card className="mb-4 border-destructive/40 bg-destructive/5">
            <CardContent className="p-4 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <p>{error}</p>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={fetchRfps}>
                  Refresh
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setError(null)}>
                  Dismiss
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <StatsCards stats={stats} />

        <SavedSearchesPanel
          savedSearches={savedSearches}
          activeSearchId={activeSearchId}
          onSearchRun={handleSearchRun}
          onSearchClear={handleSearchClear}
          onSearchesUpdated={setSavedSearches}
          onError={setError}
        />

        {/* Search and Filters */}
        <div className="flex items-center gap-4 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search opportunities..."
              className="w-full h-10 pl-10 pr-4 rounded-lg bg-secondary border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Button variant="outline">
            <Filter className="w-4 h-4" />
            Filters
          </Button>
          <Button
            variant={showCreateRfp ? "default" : "outline"}
            onClick={() => setShowCreateRfp((prev) => !prev)}
          >
            <Plus className="w-4 h-4" />
            Add RFP
          </Button>
        </div>

        {showCreateRfp && (
          <CreateRfpForm
            onCreated={fetchRfps}
            onCancel={() => setShowCreateRfp(false)}
            onError={setError}
          />
        )}

        <OpportunitiesTable
          rfps={sortedRfps}
          isLoading={isLoading}
          searchQuery={searchQuery}
          isSyncing={isSyncing}
          syncCooldownSeconds={syncCooldownSeconds}
          onSync={handleSync}
        />
      </div>
    </div>
  );
}
