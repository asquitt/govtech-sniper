"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ScoringSummary } from "@/types";
import { reviewApi } from "@/lib/api/reviews";

interface ReviewScoringSummaryProps {
  reviewId: number;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-500",
  major: "bg-orange-500",
  minor: "bg-yellow-500",
  suggestion: "bg-blue-500",
};

export function ReviewScoringSummary({ reviewId }: ReviewScoringSummaryProps) {
  const [summary, setSummary] = useState<ScoringSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSummary = useCallback(async () => {
    setLoading(true);
    try {
      const data = await reviewApi.getScoringSummary(reviewId);
      setSummary(data);
    } catch (err) {
      console.error("Failed to load scoring summary:", err);
    } finally {
      setLoading(false);
    }
  }, [reviewId]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground">Loading scoring summary...</p>
        </CardContent>
      </Card>
    );
  }

  if (!summary) return null;

  const totalSevComments = Object.values(summary.comments_by_severity).reduce((a, b) => a + b, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Scoring Summary
          <Badge variant="secondary">{summary.review_type.toUpperCase()}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Score */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <p className="text-2xl font-bold text-primary">
              {summary.average_score != null ? summary.average_score.toFixed(1) : "—"}
            </p>
            <p className="text-xs text-muted-foreground">Score</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <p className="text-2xl font-bold text-primary">
              {summary.checklist_pass_rate.toFixed(0)}%
            </p>
            <p className="text-xs text-muted-foreground">Checklist Pass</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <p className="text-2xl font-bold text-primary">
              {summary.resolution_rate.toFixed(0)}%
            </p>
            <p className="text-xs text-muted-foreground">Resolved</p>
          </div>
        </div>

        {/* Comments by severity */}
        {totalSevComments > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Comments by Severity</p>
            <div className="space-y-1.5">
              {Object.entries(summary.comments_by_severity).map(([sev, count]) => {
                const pct = totalSevComments ? (count / totalSevComments) * 100 : 0;
                return (
                  <div key={sev} className="flex items-center gap-2 text-sm">
                    <span className="w-20 capitalize text-muted-foreground">{sev}</span>
                    <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className={`h-full rounded-full ${SEVERITY_COLORS[sev] ?? "bg-gray-500"}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-8 text-right text-muted-foreground">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Resolution */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {summary.resolved_comments} of {summary.total_comments} comments resolved
          </span>
          <div className="w-24 h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${summary.resolution_rate}%` }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
