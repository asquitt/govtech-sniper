"use client";

import React from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, CheckCircle2, Clock, ExternalLink } from "lucide-react";
import type { ReviewDashboardItem, ReviewType, ReviewStatus } from "@/types";

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

export interface ReviewCardProps {
  item: ReviewDashboardItem;
  now: number;
}

export function ReviewCard({ item, now }: ReviewCardProps) {
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
              <span className="text-xs font-normal text-muted-foreground ml-1">open</span>
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Reviewers</p>
            <p className="font-mono font-bold">
              {item.completed_assignments}/{item.total_assignments}
              <span className="text-xs font-normal text-muted-foreground ml-1">done</span>
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Score</p>
            <p className="font-mono font-bold">
              {item.overall_score != null
                ? `${item.overall_score.toFixed(0)}%`
                : "\u2014"}
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
                : "\u2014"}
            </p>
          </div>
        </div>

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
