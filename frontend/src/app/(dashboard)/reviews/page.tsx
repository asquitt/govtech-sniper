"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { reviewApi } from "@/lib/api";
import type { ReviewDashboardItem, ReviewPacket, ReviewType, ReviewStatus } from "@/types";
import { ClipboardCheck, AlertCircle, CheckCircle2, Clock, ExternalLink, FileText } from "lucide-react";

const REVIEW_TYPE_COLORS: Record<ReviewType, string> = {
  pink: "bg-pink-500/10 text-pink-600 border-pink-200",
  red: "bg-red-500/10 text-red-600 border-red-200",
  gold: "bg-yellow-500/10 text-yellow-600 border-yellow-200",
};

const STATUS_ICONS: Record<ReviewStatus, React.ReactNode> = {
  scheduled: <Clock className="w-4 h-4 text-muted-foreground" />,
  in_progress: <AlertCircle className="w-4 h-4 text-blue-500" />,
  completed: <CheckCircle2 className="w-4 h-4 text-green-500" />,
  cancelled: <AlertCircle className="w-4 h-4 text-muted-foreground" />,
};

function ReviewCard({ item, now }: { item: ReviewDashboardItem; now: number }) {
  const assignmentProgress =
    item.total_assignments > 0
      ? Math.round((item.completed_assignments / item.total_assignments) * 100)
      : 0;

  const isDueSoon =
    item.scheduled_date &&
    item.status !== "completed" &&
    new Date(item.scheduled_date) < new Date(now + 3 * 86400000);

  const isOverdue =
    item.scheduled_date &&
    item.status !== "completed" &&
    new Date(item.scheduled_date) < new Date(now);

  return (
    <Card className="hover:border-primary/40 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {STATUS_ICONS[item.status]}
            <CardTitle className="text-sm font-medium">
              <Link
                href={`/proposals/${item.proposal_id}`}
                className="hover:underline inline-flex items-center gap-1"
              >
                {item.proposal_title}
                <ExternalLink className="w-3 h-3 opacity-50" />
              </Link>
            </CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={REVIEW_TYPE_COLORS[item.review_type]}>
              {item.review_type.toUpperCase()} Team
            </Badge>
            <Badge variant="outline">{item.status.replace("_", " ")}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Comments</p>
            <p className="font-mono font-bold">
              {item.open_comments}/{item.total_comments}
              <span className="text-xs font-normal text-muted-foreground ml-1">
                open
              </span>
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Reviewers</p>
            <p className="font-mono font-bold">
              {item.completed_assignments}/{item.total_assignments}
              <span className="text-xs font-normal text-muted-foreground ml-1">
                done
              </span>
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Score</p>
            <p className="font-mono font-bold">
              {item.overall_score != null
                ? `${item.overall_score.toFixed(0)}%`
                : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Due</p>
            <p
              className={`text-sm font-medium ${
                isOverdue
                  ? "text-red-600"
                  : isDueSoon
                    ? "text-yellow-600"
                    : ""
              }`}
            >
              {item.scheduled_date
                ? new Date(item.scheduled_date).toLocaleDateString()
                : "—"}
            </p>
          </div>
        </div>

        {/* Assignment progress bar */}
        {item.total_assignments > 0 && (
          <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${assignmentProgress}%` }}
            />
          </div>
        )}

        {item.go_no_go_decision && (
          <Badge
            variant={
              item.go_no_go_decision === "go"
                ? "success"
                : item.go_no_go_decision === "no_go"
                  ? "destructive"
                  : "warning"
            }
          >
            {item.go_no_go_decision === "go"
              ? "GO"
              : item.go_no_go_decision === "no_go"
                ? "NO-GO"
                : "Conditional"}
          </Badge>
        )}
      </CardContent>
    </Card>
  );
}

export default function ReviewsPage() {
  const [items, setItems] = useState<ReviewDashboardItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterType, setFilterType] = useState<ReviewType | "all">("all");
  const [filterStatus, setFilterStatus] = useState<ReviewStatus | "all">("all");
  const [selectedReviewId, setSelectedReviewId] = useState<number | null>(null);
  const [packet, setPacket] = useState<ReviewPacket | null>(null);
  const [isPacketLoading, setIsPacketLoading] = useState(false);
  const [packetError, setPacketError] = useState<string | null>(null);
  const [now] = useState(() => Date.now());

  const fetchDashboard = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await reviewApi.getDashboard();
      setItems(data);
      setSelectedReviewId((existing) => {
        if (existing && data.some((item) => item.review_id === existing)) {
          return existing;
        }
        return data[0]?.review_id ?? null;
      });
    } catch (err) {
      console.error("Failed to load review dashboard", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const fetchPacket = useCallback(async (reviewId: number) => {
    try {
      setPacketError(null);
      setIsPacketLoading(true);
      const response = await reviewApi.getReviewPacket(reviewId);
      setPacket(response);
    } catch (err) {
      console.error("Failed to load review packet", err);
      setPacket(null);
      setPacketError("Failed to load review packet.");
    } finally {
      setIsPacketLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedReviewId) {
      setPacket(null);
      return;
    }
    fetchPacket(selectedReviewId);
  }, [selectedReviewId, fetchPacket]);

  const filtered = items.filter((item) => {
    if (filterType !== "all" && item.review_type !== filterType) return false;
    if (filterStatus !== "all" && item.status !== filterStatus) return false;
    return true;
  });

  return (
    <div className="flex flex-col h-full">
      <Header title="Review Dashboard" />
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Filters */}
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            {(["all", "pink", "red", "gold"] as const).map((t) => (
              <Button
                key={t}
                size="sm"
                variant={filterType === t ? "default" : "outline"}
                onClick={() => setFilterType(t)}
              >
                {t === "all" ? "All Types" : `${t.toUpperCase()} Team`}
              </Button>
            ))}
          </div>
          <div className="flex gap-1">
            {(
              ["all", "scheduled", "in_progress", "completed"] as const
            ).map((s) => (
              <Button
                key={s}
                size="sm"
                variant={filterStatus === s ? "default" : "outline"}
                onClick={() => setFilterStatus(s)}
              >
                {s === "all"
                  ? "All Status"
                  : s.replace("_", " ").replace(/\b\w/g, (c) =>
                      c.toUpperCase()
                    )}
              </Button>
            ))}
          </div>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4 text-center">
              <p className="text-2xl font-bold">{items.length}</p>
              <p className="text-xs text-muted-foreground">Total Reviews</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 text-center">
              <p className="text-2xl font-bold text-blue-500">
                {items.filter((i) => i.status === "in_progress").length}
              </p>
              <p className="text-xs text-muted-foreground">In Progress</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 text-center">
              <p className="text-2xl font-bold text-yellow-500">
                {items.reduce((sum, i) => sum + i.open_comments, 0)}
              </p>
              <p className="text-xs text-muted-foreground">Open Comments</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 text-center">
              <p className="text-2xl font-bold text-green-500">
                {items.filter((i) => i.status === "completed").length}
              </p>
              <p className="text-xs text-muted-foreground">Completed</p>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Review Packet Builder
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={selectedReviewId ?? ""}
                onChange={(event) =>
                  setSelectedReviewId(
                    event.target.value ? Number.parseInt(event.target.value, 10) : null
                  )
                }
                className="rounded border border-border bg-background px-2 py-1 text-sm"
              >
                {items.length === 0 && <option value="">No reviews available</option>}
                {items.map((item) => (
                  <option key={item.review_id} value={item.review_id}>
                    {item.review_type.toUpperCase()} · {item.proposal_title}
                  </option>
                ))}
              </select>
              <Button
                size="sm"
                variant="outline"
                disabled={!selectedReviewId || isPacketLoading}
                onClick={() => selectedReviewId && fetchPacket(selectedReviewId)}
              >
                Refresh Packet
              </Button>
            </div>

            {isPacketLoading && (
              <p className="text-sm text-muted-foreground">Generating review packet...</p>
            )}
            {packetError && <p className="text-sm text-destructive">{packetError}</p>}

            {packet && (
              <div className="space-y-3">
                <div className="grid grid-cols-4 gap-3 text-sm">
                  <div className="rounded border border-border p-2">
                    <p className="text-xs text-muted-foreground">Risk Level</p>
                    <p className="font-semibold capitalize">{packet.risk_summary.overall_risk_level}</p>
                  </div>
                  <div className="rounded border border-border p-2">
                    <p className="text-xs text-muted-foreground">Open Critical</p>
                    <p className="font-semibold">{packet.risk_summary.open_critical}</p>
                  </div>
                  <div className="rounded border border-border p-2">
                    <p className="text-xs text-muted-foreground">Open Major</p>
                    <p className="font-semibold">{packet.risk_summary.open_major}</p>
                  </div>
                  <div className="rounded border border-border p-2">
                    <p className="text-xs text-muted-foreground">Checklist Pass</p>
                    <p className="font-semibold">{packet.checklist_summary.pass_rate.toFixed(1)}%</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="text-sm font-medium">Risk-Ranked Action Queue</p>
                  {packet.action_queue.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No actionable review comments.</p>
                  ) : (
                    <div className="space-y-2">
                      {packet.action_queue.slice(0, 5).map((action) => (
                        <div
                          key={action.comment_id}
                          className="rounded border border-border p-2 text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-medium">
                              #{action.rank} · {action.severity.toUpperCase()}
                            </span>
                            <span className="font-mono">Risk {action.risk_score.toFixed(1)}</span>
                          </div>
                          <p className="text-muted-foreground">{action.recommended_action}</p>
                          <p className="text-muted-foreground">{action.rationale}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <p className="text-sm font-medium">Exit Criteria</p>
                  <ul className="list-disc pl-5 text-xs text-muted-foreground space-y-1">
                    {packet.recommended_exit_criteria.map((criterion) => (
                      <li key={criterion}>{criterion}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Review list */}
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <ClipboardCheck className="w-6 h-6 animate-pulse text-muted-foreground" />
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-12">
            No reviews found. Schedule a review from a proposal page.
          </p>
        ) : (
          <div className="space-y-3">
            {filtered.map((item) => (
              <ReviewCard key={item.review_id} item={item} now={now} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
