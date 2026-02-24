"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface AutomationCardProps {
  isIngestingNews: boolean;
  isAnalyzingBudget: boolean;
  isRescoring: boolean;
  isPreviewingDigest: boolean;
  isSendingDigest: boolean;
  onIngestNews: () => void;
  onAnalyzeBudget: () => void;
  onRescore: () => void;
  onPreviewDigest: () => void;
  onSendDigest: () => void;
}

export function AutomationCard({
  isIngestingNews,
  isAnalyzingBudget,
  isRescoring,
  isPreviewingDigest,
  isSendingDigest,
  onIngestNews,
  onAnalyzeBudget,
  onRescore,
  onPreviewDigest,
  onSendDigest,
}: AutomationCardProps) {
  return (
    <Card data-testid="signals-automation-card">
      <CardHeader>
        <CardTitle>Automation</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Button size="sm" variant="outline" onClick={onIngestNews} disabled={isIngestingNews}>
          {isIngestingNews ? "Ingesting..." : "Ingest News"}
        </Button>
        <Button size="sm" variant="outline" onClick={onAnalyzeBudget} disabled={isAnalyzingBudget}>
          {isAnalyzingBudget ? "Analyzing..." : "Analyze Budget Docs"}
        </Button>
        <Button size="sm" variant="outline" onClick={onRescore} disabled={isRescoring}>
          {isRescoring ? "Rescoring..." : "Rescore Signals"}
        </Button>
        <Button size="sm" variant="outline" onClick={onPreviewDigest} disabled={isPreviewingDigest}>
          {isPreviewingDigest ? "Loading..." : "Preview Digest"}
        </Button>
        <Button size="sm" onClick={onSendDigest} disabled={isSendingDigest}>
          {isSendingDigest ? "Sending..." : "Send Digest"}
        </Button>
      </CardContent>
    </Card>
  );
}
