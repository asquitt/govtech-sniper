"use client";

import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ReviewComment, CommentSeverity, CommentStatus } from "@/types";
import { reviewApi } from "@/lib/api/reviews";

interface ReviewCommentListProps {
  reviewId: number;
  onRefresh?: () => void;
}

const SEVERITY_VARIANT: Record<CommentSeverity, "destructive" | "warning" | "secondary" | "default"> = {
  critical: "destructive",
  major: "warning",
  minor: "secondary",
  suggestion: "default",
};

const STATUS_VARIANT: Record<CommentStatus, "destructive" | "warning" | "success" | "secondary"> = {
  open: "warning",
  accepted: "success",
  rejected: "destructive",
  resolved: "success",
};

type SortKey = "severity" | "status" | "created_at";

const SEVERITY_ORDER: Record<CommentSeverity, number> = {
  critical: 0,
  major: 1,
  minor: 2,
  suggestion: 3,
};

export function ReviewCommentList({ reviewId, onRefresh }: ReviewCommentListProps) {
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<SortKey>("severity");

  useEffect(() => {
    loadComments();
  }, [reviewId]);

  const loadComments = async () => {
    setLoading(true);
    try {
      const data = await reviewApi.listComments(reviewId);
      setComments(data);
    } catch (err) {
      console.error("Failed to load comments:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = async (commentId: number, status: CommentStatus) => {
    try {
      await reviewApi.updateComment(reviewId, commentId, { status });
      await loadComments();
      onRefresh?.();
    } catch (err) {
      console.error("Failed to update comment:", err);
    }
  };

  const sorted = [...comments].sort((a, b) => {
    if (sortBy === "severity") {
      return SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity];
    }
    if (sortBy === "status") {
      return a.status.localeCompare(b.status);
    }
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  // Group by section
  const grouped: Record<string, ReviewComment[]> = {};
  for (const c of sorted) {
    const key = c.section_id != null ? `Section ${c.section_id}` : "General";
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(c);
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground">Loading comments...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Review Comments ({comments.length})</CardTitle>
        <div className="flex gap-1">
          {(["severity", "status", "created_at"] as SortKey[]).map((key) => (
            <Button
              key={key}
              size="sm"
              variant={sortBy === key ? "default" : "outline"}
              onClick={() => setSortBy(key)}
            >
              {key === "created_at" ? "Date" : key.charAt(0).toUpperCase() + key.slice(1)}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {comments.length === 0 ? (
          <p className="text-sm text-muted-foreground">No comments yet.</p>
        ) : (
          <div className="space-y-6">
            {Object.entries(grouped).map(([section, sectionComments]) => (
              <div key={section}>
                <h4 className="mb-2 text-sm font-medium text-muted-foreground">{section}</h4>
                <div className="space-y-2">
                  {sectionComments.map((comment) => (
                    <div
                      key={comment.id}
                      className="rounded-lg border border-border p-3 space-y-2"
                    >
                      <div className="flex items-center gap-2">
                        <Badge variant={SEVERITY_VARIANT[comment.severity]}>
                          {comment.severity}
                        </Badge>
                        <Badge variant={STATUS_VARIANT[comment.status]}>
                          {comment.status}
                        </Badge>
                        <span className="ml-auto text-xs text-muted-foreground">
                          {new Date(comment.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-sm">{comment.comment_text}</p>
                      {comment.resolution_note && (
                        <p className="text-xs text-muted-foreground italic">
                          Resolution: {comment.resolution_note}
                        </p>
                      )}
                      {comment.status === "open" && (
                        <div className="flex gap-1 pt-1">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleStatusUpdate(comment.id, "accepted")}
                          >
                            Accept
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleStatusUpdate(comment.id, "resolved")}
                          >
                            Resolve
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleStatusUpdate(comment.id, "rejected")}
                          >
                            Reject
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
