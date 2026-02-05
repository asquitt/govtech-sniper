"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Calendar,
  Building2,
  ExternalLink,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { rfpApi } from "@/lib/api";
import { cn, daysUntilDeadline, formatDate, getDeadlineUrgency } from "@/lib/utils";
import type { RFP, RFPStatus } from "@/types";

type Snapshot = {
  id: number;
  notice_id: string;
  solicitation_number?: string | null;
  rfp_id: number;
  user_id?: number | null;
  fetched_at: string;
  posted_date?: string | null;
  response_deadline?: string | null;
  raw_hash: string;
  summary: Record<string, unknown>;
  raw_payload?: Record<string, unknown> | null;
};

type SnapshotDiff = {
  from_snapshot_id: number;
  to_snapshot_id: number;
  changes: { field: string; before?: string | null; after?: string | null }[];
  summary_from: Record<string, unknown>;
  summary_to: Record<string, unknown>;
};

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

function formatSummaryValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return value.toString();
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

export default function OpportunityDetailPage() {
  const params = useParams();
  const rfpId = parseInt(params.rfpId as string, 10);

  const [rfp, setRfp] = useState<RFP | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [diff, setDiff] = useState<SnapshotDiff | null>(null);
  const [fromSnapshotId, setFromSnapshotId] = useState<number | null>(null);
  const [toSnapshotId, setToSnapshotId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "changes">("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [isDiffLoading, setIsDiffLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const summaryFields = useMemo(
    () => [
      { label: "Title", key: "title" },
      { label: "Agency", key: "agency" },
      { label: "Sub-Agency", key: "sub_agency" },
      { label: "NAICS", key: "naics_code" },
      { label: "Set-Aside", key: "set_aside" },
      { label: "Posted", key: "posted_date" },
      { label: "Deadline", key: "response_deadline" },
      { label: "Type", key: "rfp_type" },
      { label: "Resources", key: "resource_links_count" },
    ],
    []
  );

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [rfpData, snapshotData] = await Promise.all([
        rfpApi.get(rfpId),
        rfpApi.getSnapshots(rfpId, { limit: 20 }),
      ]);
      setRfp(rfpData);
      setSnapshots(snapshotData);

      if (snapshotData.length >= 2) {
        setToSnapshotId(snapshotData[0].id);
        setFromSnapshotId(snapshotData[1].id);
      } else if (snapshotData.length === 1) {
        setToSnapshotId(snapshotData[0].id);
        setFromSnapshotId(null);
      } else {
        setToSnapshotId(null);
        setFromSnapshotId(null);
      }
    } catch (err) {
      console.error("Failed to load opportunity", err);
      setError("Failed to load opportunity data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [rfpId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    const fetchDiff = async () => {
      if (!fromSnapshotId || !toSnapshotId || fromSnapshotId === toSnapshotId) {
        setDiff(null);
        return;
      }

      try {
        setIsDiffLoading(true);
        const diffData = await rfpApi.getSnapshotDiff(rfpId, {
          from_snapshot_id: fromSnapshotId,
          to_snapshot_id: toSnapshotId,
        });
        setDiff(diffData);
      } catch (diffErr) {
        console.error("Failed to load snapshot diff", diffErr);
        setDiff(null);
      } finally {
        setIsDiffLoading(false);
      }
    };

    fetchDiff();
  }, [fromSnapshotId, toSnapshotId, rfpId]);

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Opportunity" description="Loading opportunity details" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      </div>
    );
  }

  if (error || !rfp) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Opportunity" description="Unable to load opportunity" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={fetchData}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title={rfp.title}
        description={`${rfp.agency} • ${rfp.solicitation_number || rfp.id}`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" asChild>
              <Link href="/opportunities">
                <ArrowLeft className="w-4 h-4" />
                Back
              </Link>
            </Button>
            <Button asChild>
              <Link href={`/analysis/${rfp.id}`}>Analyze</Link>
            </Button>
            {rfp.sam_gov_link && (
              <Button variant="outline" asChild>
                <a href={rfp.sam_gov_link} target="_blank" rel="noreferrer">
                  <ExternalLink className="w-4 h-4" />
                  SAM.gov
                </a>
              </Button>
            )}
          </div>
        }
      />

      <div className="flex-1 p-6 overflow-auto space-y-6">
        <div className="flex items-center gap-2">
          <Button
            variant={activeTab === "overview" ? "default" : "outline"}
            onClick={() => setActiveTab("overview")}
          >
            Overview
          </Button>
          <Button
            variant={activeTab === "changes" ? "default" : "outline"}
            onClick={() => setActiveTab("changes")}
          >
            Changes
          </Button>
        </div>

        {activeTab === "overview" && (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <Card className="border border-border">
                <CardContent className="p-4 space-y-2">
                  <p className="text-xs text-muted-foreground">Status</p>
                  <Badge variant={statusConfig[rfp.status]?.variant || "default"}>
                    {statusConfig[rfp.status]?.label || rfp.status}
                  </Badge>
                </CardContent>
              </Card>
              <Card className="border border-border">
                <CardContent className="p-4 space-y-2">
                  <p className="text-xs text-muted-foreground">Qualification</p>
                  {rfp.is_qualified ? (
                    <div className="flex items-center gap-2 text-sm">
                      <CheckCircle2 className="w-4 h-4 text-success" />
                      Qualified ({rfp.qualification_score ?? 0}% match)
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-sm">
                      <Clock className="w-4 h-4 text-warning" />
                      Pending qualification
                    </div>
                  )}
                </CardContent>
              </Card>
              <Card className="border border-border">
                <CardContent className="p-4 space-y-2">
                  <p className="text-xs text-muted-foreground">Deadline</p>
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <DeadlineBadge deadline={rfp.response_deadline} />
                      <p className="text-xs text-muted-foreground">
                        {formatDate(rfp.response_deadline)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Card className="border border-border">
                <CardContent className="p-4 space-y-3">
                  <p className="text-sm font-medium">Summary</p>
                  <p className="text-sm text-muted-foreground whitespace-pre-line">
                    {rfp.summary || rfp.description || "No summary available."}
                  </p>
                </CardContent>
              </Card>
              <Card className="border border-border">
                <CardContent className="p-4 space-y-3">
                  <p className="text-sm font-medium">Opportunity Details</p>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-muted-foreground" />
                      <span>{rfp.agency}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-muted-foreground" />
                      <span>{rfp.solicitation_number || rfp.id}</span>
                    </div>
                    <div>
                      <span className="text-xs text-muted-foreground">NAICS</span>
                      <p>{rfp.naics_code || "—"}</p>
                    </div>
                    <div>
                      <span className="text-xs text-muted-foreground">Set-Aside</span>
                      <p>{rfp.set_aside || "—"}</p>
                    </div>
                    <div>
                      <span className="text-xs text-muted-foreground">Estimated Value</span>
                      <p>
                        {rfp.estimated_value
                          ? `$${rfp.estimated_value.toLocaleString()}`
                          : "—"}
                      </p>
                    </div>
                    <div>
                      <span className="text-xs text-muted-foreground">
                        Place of Performance
                      </span>
                      <p>{rfp.place_of_performance || "—"}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="border border-border">
              <CardContent className="p-4 space-y-2">
                <p className="text-sm font-medium">Source Links</p>
                <div className="space-y-2 text-sm">
                  {rfp.source_url && (
                    <a
                      href={rfp.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-2 text-primary hover:underline"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Source URL
                    </a>
                  )}
                  {rfp.sam_gov_link && (
                    <a
                      href={rfp.sam_gov_link}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-2 text-primary hover:underline"
                    >
                      <ExternalLink className="w-4 h-4" />
                      SAM.gov Link
                    </a>
                  )}
                  {!rfp.source_url && !rfp.sam_gov_link && (
                    <p className="text-muted-foreground">No links available.</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "changes" && (
          <div className="grid gap-6 lg:grid-cols-[2fr_3fr]">
            <Card className="border border-border">
              <CardContent className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">Snapshots</p>
                  <span className="text-xs text-muted-foreground">
                    {snapshots.length} total
                  </span>
                </div>
                {snapshots.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No snapshots available.</p>
                ) : (
                  <ScrollArea className="h-[420px] pr-2">
                    <div className="space-y-3">
                      {snapshots.map((snapshot) => (
                        <div
                          key={snapshot.id}
                          className="rounded-lg border border-border p-3 text-xs space-y-2"
                        >
                          <div className="flex items-center justify-between">
                            <p className="font-medium">Snapshot {snapshot.id}</p>
                            <span className="text-muted-foreground">
                              {formatDate(snapshot.fetched_at)}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            {summaryFields.map((field) => (
                              <div key={`${snapshot.id}-${field.key}`}>
                                <p className="text-muted-foreground">{field.label}</p>
                                <p>{formatSummaryValue(snapshot.summary[field.key])}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardContent className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Snapshot Diff</p>
                    <p className="text-xs text-muted-foreground">
                      Compare any two snapshots for changes
                    </p>
                  </div>
                  {isDiffLoading && (
                    <span className="text-xs text-muted-foreground">Loading...</span>
                  )}
                </div>

                {snapshots.length < 2 ? (
                  <p className="text-sm text-muted-foreground">
                    At least two snapshots are required to view changes.
                  </p>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="text-xs text-muted-foreground">
                      From Snapshot
                      <select
                        className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                        value={fromSnapshotId ?? ""}
                        onChange={(e) => setFromSnapshotId(Number(e.target.value))}
                      >
                        {snapshots.map((snapshot) => (
                          <option key={snapshot.id} value={snapshot.id}>
                            {snapshot.id} ({formatDate(snapshot.fetched_at)})
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-xs text-muted-foreground">
                      To Snapshot
                      <select
                        className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                        value={toSnapshotId ?? ""}
                        onChange={(e) => setToSnapshotId(Number(e.target.value))}
                      >
                        {snapshots.map((snapshot) => (
                          <option key={snapshot.id} value={snapshot.id}>
                            {snapshot.id} ({formatDate(snapshot.fetched_at)})
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                )}

                {diff && diff.changes.length > 0 ? (
                  <div className="space-y-3">
                    {diff.changes.map((change, index) => (
                      <div
                        key={`${change.field}-${index}`}
                        className="grid grid-cols-3 gap-3 text-xs border border-border rounded-lg p-3"
                      >
                        <div className="text-muted-foreground">
                          <span className="font-medium text-foreground">
                            {change.field}
                          </span>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Before</p>
                          <p className="text-foreground">
                            {change.before || "—"}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">After</p>
                          <p className="text-foreground">
                            {change.after || "—"}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {snapshots.length >= 2
                      ? "No changes detected for selected snapshots."
                      : ""}
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
