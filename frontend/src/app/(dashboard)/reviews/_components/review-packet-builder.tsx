"use client";

import React from "react";
import { FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ReviewDashboardItem, ReviewPacket } from "@/types";

export interface ReviewPacketBuilderProps {
  items: ReviewDashboardItem[];
  selectedReviewId: number | null;
  packet: ReviewPacket | null;
  isPacketLoading: boolean;
  packetError: string | null;
  onSelectReview: (id: number | null) => void;
  onRefresh: () => void;
}

export function ReviewPacketBuilder({
  items,
  selectedReviewId,
  packet,
  isPacketLoading,
  packetError,
  onSelectReview,
  onRefresh,
}: ReviewPacketBuilderProps) {
  return (
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
              onSelectReview(
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
            onClick={onRefresh}
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
  );
}
