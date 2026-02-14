"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Loader2, Bot, User, ThumbsUp, ThumbsDown, AlertTriangle, Radar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { captureApi } from "@/lib/api";
import type { BidScenarioRequest, BidScenarioSimulationResponse } from "@/types";

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

interface ScenarioDraft {
  id: string;
  name: string;
  notes: string;
  enabled: boolean;
  scale: number;
  adjustments: Array<{ criterion: string; delta: number; reason?: string }>;
}

const DEFAULT_SCENARIO_DRAFTS: ScenarioDraft[] = [
  {
    id: "incumbent_response",
    name: "Aggressive Incumbent Response",
    notes: "Stress-test against incumbent price pressure and relationship advantage.",
    enabled: true,
    scale: 1,
    adjustments: [
      { criterion: "competitive_landscape", delta: -22, reason: "Incumbent response pressure." },
      { criterion: "price_competitiveness", delta: -18, reason: "Likely margin compression." },
      { criterion: "relationship_with_agency", delta: -12, reason: "Agency comfort with incumbent." },
    ],
  },
  {
    id: "capacity_shock",
    name: "Execution Capacity Shock",
    notes: "Model staffing and proposal schedule disruption during pursuit.",
    enabled: true,
    scale: 1,
    adjustments: [
      { criterion: "staffing_availability", delta: -20, reason: "Key staffing shortfall." },
      { criterion: "proposal_timeline", delta: -15, reason: "Compressed timeline." },
      { criterion: "technical_capability", delta: -10, reason: "Depth constrained by resources." },
    ],
  },
  {
    id: "compliance_amendment",
    name: "Compliance Surprise Amendment",
    notes: "Late amendment tightens eligibility and vehicle requirements.",
    enabled: true,
    scale: 1,
    adjustments: [
      { criterion: "clearance_requirements", delta: -12, reason: "New clearance burden." },
      { criterion: "set_aside_eligibility", delta: -15, reason: "Eligibility risk increased." },
      { criterion: "contract_vehicle_access", delta: -12, reason: "Vehicle routing risk added." },
    ],
  },
  {
    id: "teaming_lift",
    name: "Strategic Teaming Lift",
    notes: "Model upside if a high-fit partner joins the opportunity.",
    enabled: true,
    scale: 1,
    adjustments: [
      { criterion: "teaming_strength", delta: 20, reason: "High-fit teaming commitment." },
      { criterion: "past_performance", delta: 12, reason: "Partner fills past-performance gap." },
      { criterion: "contract_vehicle_access", delta: 15, reason: "Vehicle access improved." },
    ],
  },
];

function formatCriterionName(value: string) {
  return value.replace(/_/g, " ");
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

function RiskBadge({ risk }: { risk: "low" | "medium" | "high" }) {
  if (risk === "high") return <Badge variant="destructive">High Risk</Badge>;
  if (risk === "medium") return <Badge variant="warning">Medium Risk</Badge>;
  return <Badge variant="success">Low Risk</Badge>;
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

  const [scenarioDrafts, setScenarioDrafts] = useState<ScenarioDraft[]>(DEFAULT_SCENARIO_DRAFTS);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulation, setSimulation] = useState<BidScenarioSimulationResponse | null>(null);
  const [simulationError, setSimulationError] = useState<string | null>(null);

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
    setSimulation(null);
    setSimulationError(null);
    setScenarioDrafts(DEFAULT_SCENARIO_DRAFTS);
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

  const buildScenarioPayload = (): BidScenarioRequest[] => {
    return scenarioDrafts
      .filter((draft) => draft.enabled)
      .map((draft) => ({
        name: draft.name,
        notes: draft.notes,
        adjustments: draft.adjustments.map((adjustment) => ({
          criterion: adjustment.criterion,
          delta: Number((adjustment.delta * draft.scale).toFixed(1)),
          reason: adjustment.reason,
        })),
      }));
  };

  const handleRunStressTest = async () => {
    const scenarios = buildScenarioPayload();
    if (scenarios.length === 0) {
      setSimulationError("Enable at least one scenario to run stress-test mode.");
      return;
    }
    try {
      setSimulationError(null);
      setIsSimulating(true);
      const result = await captureApi.simulateBidScenarios(rfpId, { scenarios });
      setSimulation(result);
    } catch (err) {
      console.error("Scenario simulator failed", err);
      setSimulationError("Failed to run scenario simulator. Try again.");
    } finally {
      setIsSimulating(false);
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

      <Button onClick={handleAiEvaluate} disabled={isEvaluating} className="w-full">
        {isEvaluating ? (
          <Loader2 className="w-4 h-4 animate-spin mr-2" />
        ) : (
          <Bot className="w-4 h-4 mr-2" />
        )}
        Run AI Bid Evaluation
      </Button>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Radar className="w-4 h-4" />
            Stress Test Mode
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Simulate upside/downside scenarios with calibrated confidence and explainable drivers.
          </p>
          {scenarioDrafts.map((draft) => (
            <div key={draft.id} className="rounded border border-border p-2">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <label className="text-sm font-medium flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={draft.enabled}
                    onChange={(event) =>
                      setScenarioDrafts((prev) =>
                        prev.map((item) =>
                          item.id === draft.id ? { ...item, enabled: event.target.checked } : item
                        )
                      )
                    }
                  />
                  {draft.name}
                </label>
                <label className="text-xs text-muted-foreground flex items-center gap-2">
                  Scale
                  <input
                    aria-label={`${draft.name} scale`}
                    type="number"
                    step="0.1"
                    min="0"
                    max="3"
                    value={draft.scale}
                    onChange={(event) =>
                      setScenarioDrafts((prev) => {
                        const parsed = Number.parseFloat(event.target.value || "1");
                        const safeScale = Number.isFinite(parsed) ? parsed : 1;
                        return prev.map((item) =>
                          item.id === draft.id ? { ...item, scale: safeScale } : item
                        );
                      })
                    }
                    className="w-16 rounded border border-border bg-background px-1 py-0.5 text-xs"
                  />
                </label>
              </div>
              <p className="text-xs text-muted-foreground mt-1">{draft.notes}</p>
            </div>
          ))}

          {simulationError && <p className="text-xs text-destructive">{simulationError}</p>}

          <Button
            variant="outline"
            onClick={handleRunStressTest}
            disabled={isSimulating || scorecards.length === 0}
            className="w-full"
          >
            {isSimulating ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <AlertTriangle className="w-4 h-4 mr-2" />
            )}
            Run Scenario Simulator
          </Button>

          {scorecards.length === 0 && (
            <p className="text-xs text-muted-foreground">
              Run an AI bid evaluation first to establish a baseline scorecard.
            </p>
          )}
        </CardContent>
      </Card>

      {simulation && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Scenario Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-xs text-muted-foreground flex flex-wrap items-center gap-2">
              <span>
                Baseline: <span className="font-mono">{simulation.baseline.overall_score.toFixed(1)}%</span>
              </span>
              <RecommendationBadge rec={simulation.baseline.recommendation} />
              <span>
                Confidence <span className="font-mono">{(simulation.baseline.confidence * 100).toFixed(0)}%</span>
              </span>
            </div>
            {simulation.baseline.scoring_method && (
              <p className="text-xs text-muted-foreground">{simulation.baseline.scoring_method}</p>
            )}

            {simulation.scenarios.map((scenario) => {
              const topDownside = scenario.driver_summary.negative[0];
              const topUpside = scenario.driver_summary.positive[0];
              const primaryRationale = scenario.scoring_rationale?.dominant_factors?.[0];
              return (
                <div key={scenario.name} className="rounded border border-border p-3 space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium">{scenario.name}</p>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs">{scenario.overall_score.toFixed(1)}%</span>
                      <RecommendationBadge rec={scenario.recommendation} />
                      <RiskBadge risk={scenario.decision_risk} />
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Confidence {(scenario.confidence * 100).toFixed(0)}% · Risk Score{" "}
                    {scenario.risk_score.toFixed(2)}
                  </p>
                  {scenario.recommendation_changed && (
                    <Badge variant="warning">Recommendation changed from baseline</Badge>
                  )}
                  {topDownside && (
                    <p className="text-xs text-muted-foreground">
                      Top downside: {formatCriterionName(topDownside.name)} ({topDownside.weighted_impact.toFixed(1)})
                    </p>
                  )}
                  {topUpside && (
                    <p className="text-xs text-muted-foreground">
                      Top upside: {formatCriterionName(topUpside.name)} (+{topUpside.weighted_impact.toFixed(1)})
                    </p>
                  )}
                  {primaryRationale && (
                    <p className="text-xs text-muted-foreground">
                      FAR/Section M anchor: {primaryRationale.far_reference} ·{" "}
                      {primaryRationale.section_m_factor}
                    </p>
                  )}
                  {scenario.ignored_adjustments.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                      Ignored adjustments:{" "}
                      {scenario.ignored_adjustments
                        .map((adjustment) => formatCriterionName(adjustment.criterion))
                        .join(", ")}
                    </p>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

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
            {sc.reasoning && <p className="text-xs text-muted-foreground">{sc.reasoning}</p>}
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
