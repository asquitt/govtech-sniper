"use client";

import React, { useEffect, useState } from "react";
import { BarChart3, CheckCircle2, XCircle } from "lucide-react";
import { draftApi } from "@/lib/api";
import type { ProposalScorecard as ScorecardType } from "@/types";

function ScoreBar({ score, label }: { score: number | null; label: string }) {
  const value = score ?? 0;
  const color =
    value >= 70 ? "bg-green-500" : value >= 50 ? "bg-yellow-500" : "bg-red-500";

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="w-24 text-muted-foreground truncate">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-muted">
        <div
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
      <span className="w-10 text-right font-mono text-xs">
        {score !== null ? `${Math.round(score)}` : "—"}
      </span>
    </div>
  );
}

export function QualityScorecard({ proposalId }: { proposalId: number }) {
  const [scorecard, setScorecard] = useState<ScorecardType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    draftApi
      .getScorecard(proposalId)
      .then((data) => {
        if (!cancelled) setScorecard(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [proposalId]);

  if (loading) {
    return (
      <div className="rounded-lg border p-4">
        <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
          <BarChart3 className="h-4 w-4" /> Quality Scorecard
        </h3>
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (!scorecard || scorecard.sections_scored === 0) {
    return (
      <div className="rounded-lg border p-4">
        <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
          <BarChart3 className="h-4 w-4" /> Quality Scorecard
        </h3>
        <p className="text-sm text-muted-foreground">
          Generate sections to see quality scores.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          <BarChart3 className="h-4 w-4" /> Quality Scorecard
        </h3>
        <div className="flex items-center gap-1.5">
          {scorecard.pink_team_ready ? (
            <>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <span className="text-xs text-green-600 font-medium">
                Pink Team Ready
              </span>
            </>
          ) : (
            <>
              <XCircle className="h-4 w-4 text-yellow-500" />
              <span className="text-xs text-yellow-600 font-medium">
                Not Ready
              </span>
            </>
          )}
        </div>
      </div>

      <div className="mb-4">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold">
            {scorecard.overall_score !== null
              ? Math.round(scorecard.overall_score)
              : "—"}
          </span>
          <span className="text-sm text-muted-foreground">/ 100</span>
        </div>
        <p className="text-xs text-muted-foreground">
          {scorecard.sections_scored} of {scorecard.sections_total} sections
          scored
        </p>
      </div>

      <div className="space-y-2">
        {scorecard.section_scores
          .filter((s) => s.quality_score !== null)
          .map((s) => (
            <ScoreBar
              key={s.section_id}
              score={s.quality_score}
              label={s.section_number}
            />
          ))}
      </div>
    </div>
  );
}
