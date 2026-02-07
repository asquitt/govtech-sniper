"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Star } from "lucide-react";
import { teamingBoardApi } from "@/lib/api/teaming";

interface PerformanceRatingFormProps {
  partnerId: number;
  rfpId?: number;
  onSubmitted?: () => void;
}

function StarRating({
  value,
  onChange,
  label,
}: {
  value: number;
  onChange: (v: number) => void;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground w-28">{label}</span>
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" onClick={() => onChange(n)} className="p-0.5">
            <Star
              className={`w-4 h-4 ${n <= value ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground"}`}
            />
          </button>
        ))}
      </div>
    </div>
  );
}

export function PerformanceRatingForm({
  partnerId,
  rfpId,
  onSubmitted,
}: PerformanceRatingFormProps) {
  const [rating, setRating] = useState(0);
  const [responsiveness, setResponsiveness] = useState(0);
  const [quality, setQuality] = useState(0);
  const [timeliness, setTimeliness] = useState(0);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (rating === 0) {
      setError("Overall rating is required");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await teamingBoardApi.createRating({
        partner_id: partnerId,
        rfp_id: rfpId,
        rating,
        responsiveness: responsiveness || undefined,
        quality: quality || undefined,
        timeliness: timeliness || undefined,
        comment: comment.trim() || undefined,
      });
      setRating(0);
      setResponsiveness(0);
      setQuality(0);
      setTimeliness(0);
      setComment("");
      onSubmitted?.();
    } catch (err) {
      setError("Failed to submit rating");
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Star className="w-4 h-4" />
          Rate Partner Performance
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <StarRating value={rating} onChange={setRating} label="Overall *" />
        <StarRating value={responsiveness} onChange={setResponsiveness} label="Responsiveness" />
        <StarRating value={quality} onChange={setQuality} label="Quality" />
        <StarRating value={timeliness} onChange={setTimeliness} label="Timeliness" />

        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Optional comment..."
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[60px] resize-none"
        />

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button size="sm" onClick={handleSubmit} disabled={submitting || rating === 0}>
          {submitting ? "Submitting..." : "Submit Rating"}
        </Button>
      </CardContent>
    </Card>
  );
}
