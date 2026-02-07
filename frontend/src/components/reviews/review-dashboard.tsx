"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ProposalReview, ReviewComment } from "@/types";
import { reviewApi } from "@/lib/api/reviews";

interface ReviewDashboardProps {
  proposalId: number;
  onScheduleClick: () => void;
}

const STATUS_VARIANT: Record<string, "default" | "secondary" | "success" | "warning" | "destructive"> = {
  scheduled: "secondary",
  in_progress: "warning",
  completed: "success",
  cancelled: "destructive",
};

const TYPE_LABEL: Record<string, string> = {
  pink: "Pink Team",
  red: "Red Team",
  gold: "Gold Team",
};

export function ReviewDashboard({ proposalId, onScheduleClick }: ReviewDashboardProps) {
  const [reviews, setReviews] = useState<ProposalReview[]>([]);
  const [commentCounts, setCommentCounts] = useState<Record<number, { total: number; open: number }>>({});
  const [loading, setLoading] = useState(true);

  const loadReviews = useCallback(async () => {
    setLoading(true);
    try {
      const data = await reviewApi.listReviews(proposalId);
      setReviews(data);

      const counts: Record<number, { total: number; open: number }> = {};
      for (const review of data) {
        try {
          const comments = await reviewApi.listComments(review.id);
          counts[review.id] = {
            total: comments.length,
            open: comments.filter((c: ReviewComment) => c.status === "open").length,
          };
        } catch {
          counts[review.id] = { total: 0, open: 0 };
        }
      }
      setCommentCounts(counts);
    } catch (err) {
      console.error("Failed to load reviews:", err);
    } finally {
      setLoading(false);
    }
  }, [proposalId]);

  useEffect(() => {
    loadReviews();
  }, [loadReviews]);

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground">Loading reviews...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Color Team Reviews</CardTitle>
        <Button size="sm" onClick={onScheduleClick}>
          Schedule Review
        </Button>
      </CardHeader>
      <CardContent>
        {reviews.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No reviews scheduled yet. Schedule a pink, red, or gold team review to begin.
          </p>
        ) : (
          <div className="space-y-3">
            {reviews.map((review) => {
              const counts = commentCounts[review.id] || { total: 0, open: 0 };
              return (
                <div
                  key={review.id}
                  className="flex items-center justify-between rounded-lg border border-border p-4"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">
                        {TYPE_LABEL[review.review_type] || review.review_type}
                      </span>
                      <Badge variant={STATUS_VARIANT[review.status] || "secondary"}>
                        {review.status.replace("_", " ")}
                      </Badge>
                    </div>
                    {review.scheduled_date && (
                      <p className="text-xs text-muted-foreground">
                        Scheduled: {new Date(review.scheduled_date).toLocaleDateString()}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      {counts.total} comment{counts.total !== 1 ? "s" : ""}
                      {counts.open > 0 && ` (${counts.open} open)`}
                    </p>
                  </div>
                  <div className="text-right">
                    {review.overall_score != null && (
                      <p className="text-lg font-semibold">{review.overall_score.toFixed(1)}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
