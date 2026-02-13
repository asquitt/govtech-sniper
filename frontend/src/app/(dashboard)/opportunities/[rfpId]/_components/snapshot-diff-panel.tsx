"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { rfpApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";

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

function formatSummaryValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "\u2014";
  if (typeof value === "number") return value.toString();
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

interface SnapshotDiffPanelProps {
  rfpId: number;
  snapshots: Snapshot[];
}

export type { Snapshot };

export function SnapshotDiffPanel({ rfpId, snapshots }: SnapshotDiffPanelProps) {
  const [fromSnapshotId, setFromSnapshotId] = useState<number | null>(
    snapshots.length >= 2 ? snapshots[1].id : null
  );
  const [toSnapshotId, setToSnapshotId] = useState<number | null>(
    snapshots.length >= 1 ? snapshots[0].id : null
  );
  const [diff, setDiff] = useState<SnapshotDiff | null>(null);
  const [isDiffLoading, setIsDiffLoading] = useState(false);

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

  return (
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
                      {change.before || "\u2014"}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">After</p>
                    <p className="text-foreground">
                      {change.after || "\u2014"}
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
  );
}
