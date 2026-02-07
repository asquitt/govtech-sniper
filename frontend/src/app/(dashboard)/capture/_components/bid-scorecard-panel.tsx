"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Loader2, Bot, User, ThumbsUp, ThumbsDown, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { captureApi } from "@/lib/api";

interface CriteriaScoreItem {
  name: string;
  weight: number;
  score: number;
  reasoning?: string;
}

interface ScorecardItem {
  id: number;
  overall_score: number | null;
  recommendation: string | null;
  confidence: number | null;
  reasoning: string | null;
  scorer_type: string;
  scorer_id: number | null;
  criteria_scores: CriteriaScoreItem[];
  created_at: string;
}

interface BidSummary {
  total_votes: number;
  ai_score: number | null;
  human_avg: number | null;
  overall_recommendation: string | null;
  bid_count: number;
  no_bid_count: number;
  conditional_count: number;
}

function RecommendationBadge({ rec }: { rec: string | null }) {
  if (!rec) return <Badge variant="outline">Pending</Badge>;
  const map: Record<string, { label: string; variant: "success" | "destructive" | "warning" }> = {
    bid: { label: "Bid", variant: "success" },
    no_bid: { label: "No-Bid", variant: "destructive" },
    conditional: { label: "Conditional", variant: "warning" },
  };
  const cfg = map[rec] ?? { label: rec, variant: "warning" as const };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

function ScoreBar({ score, weight }: { score: number; weight: number }) {
  const color =
    score >= 70 ? "bg-green-500" : score >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-40 truncate capitalize">
        {score.toFixed(0)}% - {weight}w
      </span>
      <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

export default function BidScorecardPanel({ rfpId }: { rfpId: number }) {
  const [scorecards, setScorecards] = useState<ScorecardItem[]>([]);
  const [summary, setSummary] = useState<BidSummary | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [cards, sum] = await Promise.all([
        captureApi.listScorecards(rfpId),
        captureApi.getBidSummary(rfpId),
      ]);
      setScorecards(cards as unknown as ScorecardItem[]);
      setSummary(sum as unknown as BidSummary);
    } catch (err) {
      console.error("Failed to load scorecards", err);
    } finally {
      setIsLoading(false);
    }
  }, [rfpId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAiEvaluate = async () => {
    try {
      setIsEvaluating(true);
      await captureApi.aiEvaluateBid(rfpId);
      await fetchData();
    } catch (err) {
      console.error("AI evaluation failed", err);
    } finally {
      setIsEvaluating(false);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-32">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary */}
      {summary && summary.total_votes > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Bid Decision Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-3">
              <RecommendationBadge rec={summary.overall_recommendation} />
              <span className="text-sm text-muted-foreground">
                {summary.total_votes} vote{summary.total_votes !== 1 ? "s" : ""}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="rounded bg-green-500/10 p-2">
                <ThumbsUp className="w-4 h-4 mx-auto text-green-500 mb-1" />
                <span className="font-bold">{summary.bid_count}</span> Bid
              </div>
              <div className="rounded bg-red-500/10 p-2">
                <ThumbsDown className="w-4 h-4 mx-auto text-red-500 mb-1" />
                <span className="font-bold">{summary.no_bid_count}</span> No-Bid
              </div>
              <div className="rounded bg-yellow-500/10 p-2">
                <AlertTriangle className="w-4 h-4 mx-auto text-yellow-500 mb-1" />
                <span className="font-bold">{summary.conditional_count}</span> Cond.
              </div>
            </div>
            {summary.ai_score !== null && (
              <p className="text-xs text-muted-foreground">
                AI Score: <span className="font-mono font-bold">{summary.ai_score.toFixed(0)}%</span>
                {summary.human_avg !== null && (
                  <> · Human Avg: <span className="font-mono font-bold">{summary.human_avg.toFixed(0)}%</span></>
                )}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* AI Evaluate button */}
      <Button onClick={handleAiEvaluate} disabled={isEvaluating} className="w-full">
        {isEvaluating ? (
          <Loader2 className="w-4 h-4 animate-spin mr-2" />
        ) : (
          <Bot className="w-4 h-4 mr-2" />
        )}
        Run AI Bid Evaluation
      </Button>

      {/* Scorecards */}
      {scorecards.map((sc) => (
        <Card key={sc.id}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {sc.scorer_type === "ai" ? (
                  <Bot className="w-4 h-4 text-primary" />
                ) : (
                  <User className="w-4 h-4 text-muted-foreground" />
                )}
                <span className="text-sm font-medium capitalize">{sc.scorer_type} Evaluation</span>
              </div>
              <div className="flex items-center gap-2">
                {sc.overall_score !== null && (
                  <span className="text-sm font-mono font-bold">{sc.overall_score.toFixed(0)}%</span>
                )}
                <RecommendationBadge rec={sc.recommendation} />
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {sc.reasoning && (
              <p className="text-xs text-muted-foreground">{sc.reasoning}</p>
            )}
            {sc.criteria_scores.length > 0 && (
              <div className="space-y-1">
                {sc.criteria_scores.map((cs) => (
                  <ScoreBar key={cs.name} score={cs.score} weight={cs.weight} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
