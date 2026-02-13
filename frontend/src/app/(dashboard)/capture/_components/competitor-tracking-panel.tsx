"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { captureApi } from "@/lib/api";
import type { RFP, CaptureCompetitor, CaptureMatchInsight } from "@/types";
interface CompetitorTrackingPanelProps {
  selectedRfp: RFP | null;
  competitors: CaptureCompetitor[];
  matchInsight: CaptureMatchInsight | null;
  selectedRfpId: number | null;
  onCompetitorsChange: (
    updater: (prev: CaptureCompetitor[]) => CaptureCompetitor[]
  ) => void;
  onError: (message: string) => void;
}

const fmt = (value?: string | number | null) =>
  value === null || value === undefined || value === "" ? "\u2014" : String(value);

const fmtBudget = (value?: number | null) =>
  value === null || value === undefined ? "\u2014" : `$${value.toLocaleString()}`;

export function CompetitorTrackingPanel({
  selectedRfp,
  competitors,
  matchInsight,
  selectedRfpId,
  onCompetitorsChange,
  onError,
}: CompetitorTrackingPanelProps) {
  const [competitorName, setCompetitorName] = useState("");
  const [competitorStrengths, setCompetitorStrengths] = useState("");
  const [competitorWeaknesses, setCompetitorWeaknesses] = useState("");
  const [competitorIncumbent, setCompetitorIncumbent] = useState(false);
  const [competitorNotes, setCompetitorNotes] = useState("");

  const handleCreateCompetitor = async () => {
    if (!selectedRfpId || !competitorName.trim()) return;
    try {
      const created = await captureApi.createCompetitor({
        rfp_id: selectedRfpId,
        name: competitorName.trim(),
        incumbent: competitorIncumbent,
        strengths: competitorStrengths || undefined,
        weaknesses: competitorWeaknesses || undefined,
        notes: competitorNotes || undefined,
      });
      onCompetitorsChange((prev) => [created, ...prev]);
      setCompetitorName("");
      setCompetitorStrengths("");
      setCompetitorWeaknesses("");
      setCompetitorNotes("");
      setCompetitorIncumbent(false);
    } catch (err) {
      console.error("Failed to create competitor", err);
      onError("Failed to create competitor.");
    }
  };

  const handleRemoveCompetitor = async (competitorId: number) => {
    try {
      await captureApi.removeCompetitor(competitorId);
      onCompetitorsChange((prev) =>
        prev.filter((item) => item.id !== competitorId)
      );
    } catch (err) {
      console.error("Failed to remove competitor", err);
      onError("Failed to remove competitor.");
    }
  };

  return (
    <>
      {/* Competitive Intel */}
      <div className="bg-card border border-border rounded-lg p-4 space-y-4 mt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-foreground">
              Competitive Intel
            </p>
            <p className="text-xs text-muted-foreground">
              Surface vehicles, incumbents, and buyer details for the selected
              opportunity.
            </p>
          </div>
          <Badge variant="outline">
            {selectedRfp?.source_type || "Source unknown"}
          </Badge>
        </div>

        {selectedRfp ? (
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3 text-sm">
              <div>
                <p className="text-xs text-muted-foreground">Jurisdiction</p>
                <p className="text-foreground">
                  {fmt(selectedRfp.jurisdiction)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">
                  Contract Vehicle
                </p>
                <p className="text-foreground">
                  {fmt(selectedRfp.contract_vehicle)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">
                  Incumbent Vendor
                </p>
                <p className="text-foreground">
                  {fmt(selectedRfp.incumbent_vendor)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Budget Estimate</p>
                <p className="text-foreground">
                  {fmtBudget(selectedRfp.budget_estimate)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Buyer Contact</p>
                <p className="text-foreground">
                  {fmt(selectedRfp.buyer_contact_name)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">
                  Buyer Email / Phone
                </p>
                <p className="text-foreground">
                  {fmt(selectedRfp.buyer_contact_email)}
                  {selectedRfp.buyer_contact_phone
                    ? ` \u00b7 ${selectedRfp.buyer_contact_phone}`
                    : ""}
                </p>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-md border border-border bg-background/40 p-3">
                <p className="text-xs text-muted-foreground mb-2">
                  Competitive Landscape
                </p>
                <p className="text-sm text-foreground whitespace-pre-line">
                  {fmt(selectedRfp.competitive_landscape)}
                </p>
              </div>
              <div className="rounded-md border border-border bg-background/40 p-3">
                <p className="text-xs text-muted-foreground mb-2">
                  Intel Notes
                </p>
                <p className="text-sm text-foreground whitespace-pre-line">
                  {fmt(selectedRfp.intel_notes)}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Select an opportunity to view competitive intel.
          </p>
        )}
      </div>

      {/* Bid Match Insight + Competitor Comparisons */}
      <div className="grid grid-cols-2 gap-6 mt-6">
        <div className="bg-card border border-border rounded-lg p-4 space-y-4">
          <div>
            <p className="text-sm font-medium text-foreground">
              Bid Match Insight
            </p>
            <p className="text-xs text-muted-foreground">
              Summary of fit signals for the selected capture plan.
            </p>
          </div>
          {matchInsight ? (
            <div className="space-y-3 text-sm">
              <p className="text-foreground">{matchInsight.summary}</p>
              <div className="grid gap-2 md:grid-cols-2 text-xs text-muted-foreground">
                {matchInsight.factors.map((factor, index) => (
                  <div
                    key={`${factor.factor}-${index}`}
                    className="rounded-md border border-border p-2"
                  >
                    <p className="text-foreground font-medium">
                      {factor.factor}
                    </p>
                    <p>{String(factor.value)}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Select a plan to view insight.
            </p>
          )}
        </div>

        <div className="bg-card border border-border rounded-lg p-4 space-y-4">
          <div>
            <p className="text-sm font-medium text-foreground">
              Competitor Comparisons
            </p>
            <p className="text-xs text-muted-foreground">
              Track incumbents and competitive positioning.
            </p>
          </div>

          <div className="space-y-2">
            {competitors.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No competitors tracked yet.
              </p>
            ) : (
              competitors.map((competitor) => (
                <div
                  key={competitor.id}
                  className="rounded-md border border-border p-3 text-sm space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-foreground">
                      {competitor.name}
                      {competitor.incumbent ? " (Incumbent)" : ""}
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveCompetitor(competitor.id)}
                    >
                      Remove
                    </Button>
                  </div>
                  {competitor.strengths && (
                    <p className="text-xs text-muted-foreground">
                      Strengths: {competitor.strengths}
                    </p>
                  )}
                  {competitor.weaknesses && (
                    <p className="text-xs text-muted-foreground">
                      Weaknesses: {competitor.weaknesses}
                    </p>
                  )}
                  {competitor.notes && (
                    <p className="text-xs text-muted-foreground">
                      Notes: {competitor.notes}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>

          <div className="space-y-2">
            <input
              className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
              placeholder="Competitor name"
              value={competitorName}
              onChange={(e) => setCompetitorName(e.target.value)}
            />
            <textarea
              className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
              placeholder="Strengths"
              value={competitorStrengths}
              onChange={(e) => setCompetitorStrengths(e.target.value)}
              rows={2}
            />
            <textarea
              className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
              placeholder="Weaknesses"
              value={competitorWeaknesses}
              onChange={(e) => setCompetitorWeaknesses(e.target.value)}
              rows={2}
            />
            <textarea
              className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
              placeholder="Notes"
              value={competitorNotes}
              onChange={(e) => setCompetitorNotes(e.target.value)}
              rows={2}
            />
            <label className="flex items-center gap-2 text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={competitorIncumbent}
                onChange={(e) => setCompetitorIncumbent(e.target.checked)}
              />
              Incumbent
            </label>
            <Button onClick={handleCreateCompetitor}>Add Competitor</Button>
          </div>
        </div>
      </div>
    </>
  );
}
