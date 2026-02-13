"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CapabilityGapResult } from "@/types";

interface PartnerFitAnalysisProps {
  gapRfpId: string;
  gapLoading: boolean;
  gapResult: CapabilityGapResult | null;
  onRfpIdChange: (value: string) => void;
  onAnalyze: () => void;
}

export function PartnerFitAnalysis({
  gapRfpId,
  gapLoading,
  gapResult,
  onRfpIdChange,
  onAnalyze,
}: PartnerFitAnalysisProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Partner Fit Analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              RFP ID
            </label>
            <input
              className="border rounded-lg px-3 py-2 text-sm bg-background"
              placeholder="123"
              type="number"
              min={1}
              aria-label="RFP ID"
              value={gapRfpId}
              onChange={(event) => onRfpIdChange(event.target.value)}
            />
          </div>
          <Button
            size="sm"
            onClick={onAnalyze}
            disabled={gapLoading || !gapRfpId.trim()}
          >
            Analyze Fit
          </Button>
        </div>
        {gapResult && (
          <div className="rounded-lg border border-border p-3 text-sm">
            <p className="font-medium text-foreground">{gapResult.analysis_summary}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Gaps: {gapResult.gaps.length} &middot; Recommended partners:{" "}
              {gapResult.recommended_partners.length}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
