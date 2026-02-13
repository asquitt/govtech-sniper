"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { captureApi } from "@/lib/api";
import type {
  CaptureStage,
  BidDecision,
  GateReview,
  RFPListItem,
} from "@/types";

const stageOptions: { value: CaptureStage; label: string }[] = [
  { value: "identified", label: "Identified" },
  { value: "qualified", label: "Qualified" },
  { value: "pursuit", label: "Pursuit" },
  { value: "proposal", label: "Proposal" },
  { value: "submitted", label: "Submitted" },
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" },
];

const decisionOptions: { value: BidDecision; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "bid", label: "Bid" },
  { value: "no_bid", label: "No Bid" },
];

interface GateReviewsPanelProps {
  rfps: RFPListItem[];
  selectedRfpId: number | null;
  gateReviews: GateReview[];
  onSelectRfp: (rfpId: number) => void;
  onGateReviewsChange: (reviews: GateReview[]) => void;
  onError: (message: string) => void;
}

export function GateReviewsPanel({
  rfps,
  selectedRfpId,
  gateReviews,
  onSelectRfp,
  onGateReviewsChange,
  onError,
}: GateReviewsPanelProps) {
  const [gateReviewStage, setGateReviewStage] =
    useState<CaptureStage>("qualified");
  const [gateReviewDecision, setGateReviewDecision] =
    useState<BidDecision>("pending");
  const [gateReviewNotes, setGateReviewNotes] = useState("");

  const handleCreateGateReview = async () => {
    if (!selectedRfpId) return;
    try {
      await captureApi.createGateReview({
        rfp_id: selectedRfpId,
        stage: gateReviewStage,
        decision: gateReviewDecision,
        notes: gateReviewNotes.trim() || undefined,
      });
      setGateReviewNotes("");
      const reviews = await captureApi.listGateReviews(selectedRfpId);
      onGateReviewsChange(reviews);
    } catch (err) {
      console.error("Failed to create gate review", err);
      onError("Failed to create gate review.");
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-foreground">Gate Reviews</p>
          <p className="text-xs text-muted-foreground">
            Track bid/no-bid decisions
          </p>
        </div>
        <select
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          value={selectedRfpId ?? ""}
          onChange={(e) => onSelectRfp(Number(e.target.value))}
        >
          {rfps.map((rfp) => (
            <option key={rfp.id} value={rfp.id}>
              {rfp.title}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          value={gateReviewStage}
          onChange={(e) =>
            setGateReviewStage(e.target.value as CaptureStage)
          }
        >
          {stageOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          value={gateReviewDecision}
          onChange={(e) =>
            setGateReviewDecision(e.target.value as BidDecision)
          }
        >
          {decisionOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <input
          className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Notes"
          value={gateReviewNotes}
          onChange={(e) => setGateReviewNotes(e.target.value)}
        />
        <Button onClick={handleCreateGateReview}>Add Review</Button>
      </div>

      <div className="space-y-2">
        {gateReviews.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No gate reviews yet.
          </p>
        ) : (
          gateReviews.map((review) => (
            <div
              key={review.id}
              className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
            >
              <div>
                <p className="font-medium text-foreground">
                  {review.stage} · {review.decision}
                </p>
                {review.notes && (
                  <p className="text-xs text-muted-foreground">
                    {review.notes}
                  </p>
                )}
              </div>
              <Badge variant="outline">{review.created_at.slice(0, 10)}</Badge>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
