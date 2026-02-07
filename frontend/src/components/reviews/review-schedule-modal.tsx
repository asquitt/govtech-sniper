"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import type { ReviewType } from "@/types";
import { reviewApi } from "@/lib/api/reviews";

interface ReviewScheduleModalProps {
  proposalId: number;
  open: boolean;
  onClose: () => void;
  onScheduled: () => void;
}

const REVIEW_TYPES: { value: ReviewType; label: string; description: string }[] = [
  { value: "pink", label: "Pink Team", description: "Storyboard / outline review" },
  { value: "red", label: "Red Team", description: "Full draft compliance review" },
  { value: "gold", label: "Gold Team", description: "Final quality / executive review" },
];

export function ReviewScheduleModal({
  proposalId,
  open,
  onClose,
  onScheduled,
}: ReviewScheduleModalProps) {
  const [reviewType, setReviewType] = useState<ReviewType>("pink");
  const [scheduledDate, setScheduledDate] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await reviewApi.scheduleReview(proposalId, {
        review_type: reviewType,
        scheduled_date: scheduledDate || null,
      });
      onScheduled();
      onClose();
    } catch (err) {
      console.error("Failed to schedule review:", err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-lg">
        <h2 className="mb-4 text-lg font-semibold">Schedule Color Team Review</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Review Type</label>
            <div className="space-y-2">
              {REVIEW_TYPES.map((rt) => (
                <label
                  key={rt.value}
                  className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors ${
                    reviewType === rt.value
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <input
                    type="radio"
                    name="reviewType"
                    value={rt.value}
                    checked={reviewType === rt.value}
                    onChange={() => setReviewType(rt.value)}
                    className="accent-primary"
                  />
                  <div>
                    <div className="text-sm font-medium">{rt.label}</div>
                    <div className="text-xs text-muted-foreground">{rt.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Scheduled Date</label>
            <input
              type="datetime-local"
              value={scheduledDate}
              onChange={(e) => setScheduledDate(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Scheduling..." : "Schedule Review"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
