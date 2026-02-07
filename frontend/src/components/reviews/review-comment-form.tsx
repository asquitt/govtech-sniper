"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import type { CommentSeverity } from "@/types";
import { reviewApi } from "@/lib/api/reviews";

interface ReviewCommentFormProps {
  reviewId: number;
  sectionId?: number | null;
  onAdded: () => void;
}

const SEVERITIES: { value: CommentSeverity; label: string }[] = [
  { value: "critical", label: "Critical" },
  { value: "major", label: "Major" },
  { value: "minor", label: "Minor" },
  { value: "suggestion", label: "Suggestion" },
];

export function ReviewCommentForm({ reviewId, sectionId, onAdded }: ReviewCommentFormProps) {
  const [commentText, setCommentText] = useState("");
  const [severity, setSeverity] = useState<CommentSeverity>("minor");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim()) return;

    setSubmitting(true);
    try {
      await reviewApi.addComment(reviewId, {
        section_id: sectionId ?? null,
        comment_text: commentText.trim(),
        severity,
      });
      setCommentText("");
      setSeverity("minor");
      onAdded();
    } catch (err) {
      console.error("Failed to add comment:", err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-lg border border-border p-4">
      <div>
        <label className="mb-1 block text-sm font-medium">Comment</label>
        <textarea
          value={commentText}
          onChange={(e) => setCommentText(e.target.value)}
          placeholder="Enter your review comment..."
          rows={3}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground"
        />
      </div>

      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label className="mb-1 block text-sm font-medium">Severity</label>
          <div className="flex gap-1">
            {SEVERITIES.map((s) => (
              <Button
                key={s.value}
                type="button"
                size="sm"
                variant={severity === s.value ? "default" : "outline"}
                onClick={() => setSeverity(s.value)}
              >
                {s.label}
              </Button>
            ))}
          </div>
        </div>

        <Button type="submit" disabled={submitting || !commentText.trim()}>
          {submitting ? "Adding..." : "Add Comment"}
        </Button>
      </div>
    </form>
  );
}
