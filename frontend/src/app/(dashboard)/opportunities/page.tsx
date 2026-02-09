"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import Link from "next/link";
import {
  Search,
  Filter,
  Plus,
  ExternalLink,
  MoreHorizontal,
  Target,
  Clock,
  Building2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  formatDate,
  daysUntilDeadline,
  getDeadlineUrgency,
  cn,
} from "@/lib/utils";
import { rfpApi, ingestApi, savedSearchApi } from "@/lib/api";
import type { RFPListItem, RFPStatus, SavedSearch } from "@/types";

const statusConfig: Record<
  RFPStatus,
  { label: string; variant: "default" | "success" | "warning" | "destructive" }
> = {
  new: { label: "New", variant: "default" },
  analyzing: { label: "Analyzing", variant: "warning" },
  analyzed: { label: "Analyzed", variant: "success" },
  drafting: { label: "Drafting", variant: "warning" },
  ready: { label: "Ready", variant: "success" },
  submitted: { label: "Submitted", variant: "success" },
  archived: { label: "Archived", variant: "destructive" },
};

function QualificationBadge({
  isQualified,
  score,
}: {
  isQualified?: boolean;
  score?: number;
}) {
  if (isQualified === undefined) {
    return (
      <Badge variant="outline" className="gap-1">
        <Clock className="w-3 h-3" />
        Pending
      </Badge>
    );
  }

  if (isQualified) {
    return (
      <Badge variant="success" className="gap-1">
        <CheckCircle2 className="w-3 h-3" />
        Qualified {score && `(${score}%)`}
      </Badge>
    );
  }

  return (
    <Badge variant="destructive" className="gap-1">
      <XCircle className="w-3 h-3" />
      Not Qualified
    </Badge>
  );
}

function MatchScoreBadge({ score }: { score?: number | null }) {
  if (score === undefined || score === null) {
    return <span className="text-muted-foreground text-xs">—</span>;
  }

  const variant =
    score >= 70 ? "success" : score >= 40 ? "warning" : "destructive";
  return (
    <Badge variant={variant} className="font-mono">
      {Math.round(score)}%
    </Badge>
  );
}

function DeadlineBadge({ deadline }: { deadline?: string }) {
  const days = daysUntilDeadline(deadline);
  const urgency = getDeadlineUrgency(deadline);

  if (days === null) return <span className="text-muted-foreground">—</span>;

  const colorClass =
    urgency === "urgent"
      ? "text-destructive"
      : urgency === "warning"
      ? "text-warning"
      : "text-foreground";

  return (
    <span className={cn("flex items-center gap-1", colorClass)}>
      {urgency === "urgent" && <AlertTriangle className="w-3 h-3" />}
      {days < 0 ? "Overdue" : days === 0 ? "Today" : `${days} days`}
    </span>
  );
}

export default function OpportunitiesPage() {
  const [rfps, setRfps] = useState<RFPListItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [showRecommended, setShowRecommended] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [savedSearchName, setSavedSearchName] = useState("");
  const [savedSearchKeywords, setSavedSearchKeywords] = useState("");
  const [savedSearchAgencies, setSavedSearchAgencies] = useState("");
  const [savedSearchNaics, setSavedSearchNaics] = useState("");
  const [savedSearchSetAside, setSavedSearchSetAside] = useState("");
  const [savedSearchSourceType, setSavedSearchSourceType] = useState("");
  const [savedSearchMinValue, setSavedSearchMinValue] = useState("");
  const [savedSearchMaxValue, setSavedSearchMaxValue] = useState("");
  const [savedSearchStatus, setSavedSearchStatus] = useState<RFPStatus | "">("");
  const [activeSearchId, setActiveSearchId] = useState<number | null>(null);
  const [activeSearchMatchIds, setActiveSearchMatchIds] = useState<number[]>([]);
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

  const handleSync = async () => {
    try {
      setIsSyncing(true);
      // Trigger SAM.gov search with default parameters
      const result = await ingestApi.triggerSamSearch({
        keywords: "software",
        days_back: 30,
        limit: 100,
      });

      // Some dev/local fallbacks complete synchronously.
      if (result.status !== "completed" && result.status !== "failed") {
        // Poll for completion with a cap to avoid hanging forever.
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

      // Refresh the list
      await fetchRfps();
    } catch (err) {
      console.error("SAM.gov sync failed:", err);
      setError("Failed to sync with SAM.gov. Please try again.");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleCreateSavedSearch = async () => {
    if (!savedSearchName.trim()) return;
    try {
      const filters: Record<string, unknown> = {
        keywords: savedSearchKeywords
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        agencies: savedSearchAgencies
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        naics_codes: savedSearchNaics
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        set_asides: savedSearchSetAside
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        source_types: savedSearchSourceType
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        statuses: savedSearchStatus ? [savedSearchStatus] : [],
      };

      if (savedSearchMinValue) {
        const min = Number(savedSearchMinValue);
        if (!Number.isNaN(min)) {
          filters.min_value = min;
        }
      }

      if (savedSearchMaxValue) {
        const max = Number(savedSearchMaxValue);
        if (!Number.isNaN(max)) {
          filters.max_value = max;
        }
      }

      await savedSearchApi.create({
        name: savedSearchName.trim(),
        filters,
      });

      setSavedSearchName("");
      setSavedSearchKeywords("");
      setSavedSearchAgencies("");
      setSavedSearchNaics("");
      setSavedSearchSetAside("");
      setSavedSearchSourceType("");
      setSavedSearchMinValue("");
      setSavedSearchMaxValue("");
      setSavedSearchStatus("");

      const savedSearchList = await savedSearchApi.list();
      setSavedSearches(savedSearchList);
    } catch (err) {
      console.error("Failed to create saved search", err);
      setError("Failed to create saved search.");
    }
  };

  const handleRunSavedSearch = async (searchId: number) => {
    try {
      const result = await savedSearchApi.run(searchId);
      setActiveSearchId(searchId);
      setActiveSearchMatchIds(result.matches.map((match) => match.id));
    } catch (err) {
      console.error("Failed to run saved search", err);
      setError("Failed to run saved search.");
    }
  };

  const handleClearSavedSearch = () => {
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

  if (error && !isLoading) {
    return (
      <div className="flex flex-col h-full">
        <Header
          title="Opportunities"
          description="Track and manage government contract opportunities"
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <AlertTriangle className="w-12 h-12 text-destructive mx-auto mb-4" />
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={fetchRfps}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

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
            <Button onClick={handleSync} disabled={isSyncing}>
              {isSyncing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              Sync SAM.gov
            </Button>
          </div>
        }
      />

      <div className="flex-1 p-6 overflow-hidden">
        {/* Stats Cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total RFPs</p>
                  <p className="text-2xl font-bold text-primary">{stats.total}</p>
                </div>
                <Target className="w-8 h-8 text-primary/50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-accent/5 to-accent/10 border-accent/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Qualified</p>
                  <p className="text-2xl font-bold text-accent">
                    {stats.qualified}
                  </p>
                </div>
                <CheckCircle2 className="w-8 h-8 text-accent/50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-warning/5 to-warning/10 border-warning/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Pending Filter</p>
                  <p className="text-2xl font-bold text-warning">
                    {stats.pending}
                  </p>
                </div>
                <Clock className="w-8 h-8 text-warning/50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-secondary/50 to-secondary border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Analyzing</p>
                  <p className="text-2xl font-bold">{stats.analyzing}</p>
                </div>
                {stats.analyzing > 0 ? (
                  <Loader2 className="w-8 h-8 text-muted-foreground/50 animate-spin" />
                ) : (
                  <Loader2 className="w-8 h-8 text-muted-foreground/50" />
                )}
              </div>
            </CardContent>
          </Card>
        </div>

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
                <Button variant="outline" size="sm" onClick={handleClearSavedSearch}>
                  Clear Active Search
                </Button>
              )}
            </div>

            <div className="grid grid-cols-3 gap-3">
              <input
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Search name"
                value={savedSearchName}
                onChange={(e) => setSavedSearchName(e.target.value)}
              />
              <input
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Keywords (comma-separated)"
                value={savedSearchKeywords}
                onChange={(e) => setSavedSearchKeywords(e.target.value)}
              />
              <input
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Agencies (comma-separated)"
                value={savedSearchAgencies}
                onChange={(e) => setSavedSearchAgencies(e.target.value)}
              />
              <input
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="NAICS codes"
                value={savedSearchNaics}
                onChange={(e) => setSavedSearchNaics(e.target.value)}
              />
              <input
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Set-Asides"
                value={savedSearchSetAside}
                onChange={(e) => setSavedSearchSetAside(e.target.value)}
              />
              <input
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Source Type (federal, sled)"
                value={savedSearchSourceType}
                onChange={(e) => setSavedSearchSourceType(e.target.value)}
              />
              <input
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Min Value"
                value={savedSearchMinValue}
                onChange={(e) => setSavedSearchMinValue(e.target.value)}
              />
              <input
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Max Value"
                value={savedSearchMaxValue}
                onChange={(e) => setSavedSearchMaxValue(e.target.value)}
              />
              <select
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                value={savedSearchStatus}
                onChange={(e) =>
                  setSavedSearchStatus(e.target.value as RFPStatus | "")
                }
              >
                <option value="">Any Status</option>
                {Object.keys(statusConfig).map((status) => (
                  <option key={status} value={status}>
                    {statusConfig[status as RFPStatus].label}
                  </option>
                ))}
              </select>
            </div>

            <Button onClick={handleCreateSavedSearch} size="sm">
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
                        Last run: {search.last_run_at ? formatDate(search.last_run_at) : "—"} ·
                        Matches: {search.last_match_count}
                      </p>
                    </div>
                    <Button
                      variant={activeSearchId === search.id ? "default" : "outline"}
                      size="sm"
                      onClick={() => handleRunSavedSearch(search.id)}
                    >
                      {activeSearchId === search.id ? "Active" : "Run"}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

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
          <Button>
            <Plus className="w-4 h-4" />
            Add RFP
          </Button>
        </div>

        {/* Data Table */}
        <Card className="flex-1 overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : sortedRfps.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64">
              <Target className="w-12 h-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">
                {searchQuery
                  ? "No opportunities match your search"
                  : "No opportunities found"}
              </p>
              {!searchQuery && (
                <Button onClick={handleSync} disabled={isSyncing}>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Sync from SAM.gov
                </Button>
              )}
            </div>
          ) : (
            <ScrollArea className="h-[calc(100vh-380px)]">
              <table className="w-full">
                <thead className="sticky top-0 bg-card border-b border-border">
                  <tr className="text-left text-sm text-muted-foreground">
                    <th className="p-4 font-medium">Opportunity</th>
                    <th className="p-4 font-medium">Agency</th>
                    <th className="p-4 font-medium">Status</th>
                    <th className="p-4 font-medium">Qualification</th>
                    <th className="p-4 font-medium">Match</th>
                    <th className="p-4 font-medium">Deadline</th>
                    <th className="p-4 font-medium w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {sortedRfps.map((rfp) => (
                    <tr
                      key={rfp.id}
                      className="border-b border-border hover:bg-secondary/50 transition-colors"
                    >
                      <td className="p-4">
                        <div className="flex flex-col gap-1">
                          <Link
                            href={`/opportunities/${rfp.id}`}
                            className="font-medium text-foreground hover:text-primary transition-colors line-clamp-1"
                          >
                            {rfp.title}
                          </Link>
                          <span className="text-xs text-muted-foreground font-mono">
                            {rfp.solicitation_number || rfp.notice_id}
                          </span>
                        </div>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <Building2 className="w-4 h-4 text-muted-foreground" />
                          <span className="text-sm">{rfp.agency}</span>
                        </div>
                      </td>
                      <td className="p-4">
                        <Badge variant={statusConfig[rfp.status]?.variant || "default"}>
                          {rfp.status === "analyzing" && (
                            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                          )}
                          {statusConfig[rfp.status]?.label || rfp.status}
                        </Badge>
                      </td>
                      <td className="p-4">
                        <div className="flex flex-col gap-1">
                          <QualificationBadge
                            isQualified={rfp.is_qualified}
                            score={rfp.qualification_score}
                          />
                          {rfp.recommendation_score !== undefined && (
                            <Badge variant="outline" className="w-fit">
                              Rec {Math.round(rfp.recommendation_score)}%
                            </Badge>
                          )}
                        </div>
                      </td>
                      <td className="p-4">
                        <MatchScoreBadge score={rfp.match_score} />
                      </td>
                      <td className="p-4">
                        <div className="flex flex-col gap-0.5">
                          <DeadlineBadge deadline={rfp.response_deadline} />
                          <span className="text-xs text-muted-foreground">
                            {formatDate(rfp.response_deadline)}
                          </span>
                        </div>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" asChild>
                            <Link href={`/analysis/${rfp.id}`}>
                              <ExternalLink className="w-4 h-4" />
                            </Link>
                          </Button>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollArea>
          )}
        </Card>
      </div>
    </div>
  );
}
