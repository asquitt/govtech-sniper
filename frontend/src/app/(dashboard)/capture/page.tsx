"use client";

import React, { useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { useQueryClient } from "@tanstack/react-query";
import {
  useCaptureData,
  useCaptureDetails,
  useCreateCapturePlan,
  useUpdateCapturePlan,
} from "@/hooks/use-capture";
import BidScorecardPanel from "./_components/bid-scorecard-panel";
import { CaptureSummaryCards } from "./_components/capture-summary-cards";
import { CapturePipeline } from "./_components/capture-pipeline";
import { GateReviewsPanel } from "./_components/gate-reviews-panel";
import { TeamingPartnersPanel } from "./_components/teaming-partners-panel";
import { CompetitorTrackingPanel } from "./_components/competitor-tracking-panel";
import { CustomFieldsPanel } from "./_components/custom-fields-panel";
import type { CapturePlanListItem, CaptureStage } from "@/types";

export default function CapturePage() {
  const queryClient = useQueryClient();
  const { data: captureData, isLoading, error: fetchError } = useCaptureData();
  const createPlan = useCreateCapturePlan();
  const updatePlan = useUpdateCapturePlan();
  const [selectedRfpId, setSelectedRfpId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const rfps = captureData?.rfps ?? [];
  const plans = captureData?.plans ?? [];
  const partners = captureData?.partners ?? [];

  // Auto-select first RFP
  React.useEffect(() => {
    if (rfps.length > 0 && (selectedRfpId === null || !rfps.some((r) => r.id === selectedRfpId))) {
      setSelectedRfpId(rfps[0].id);
    }
  }, [rfps, selectedRfpId]);

  const planByRfp = useMemo(() => {
    const map = new Map<number, CapturePlanListItem>();
    plans.forEach((plan) => map.set(plan.rfp_id, plan));
    return map;
  }, [plans]);

  const plansByStage = useMemo(() => {
    const stageValues: CaptureStage[] = [
      "identified", "qualified", "pursuit", "proposal", "submitted", "won", "lost",
    ];
    const map = new Map<CaptureStage, CapturePlanListItem[]>();
    stageValues.forEach((s) => map.set(s, []));
    plans.forEach((plan) => {
      const bucket = map.get(plan.stage);
      if (bucket) bucket.push(plan);
      else map.set(plan.stage, [plan]);
    });
    return map;
  }, [plans]);

  const selectedPlan = selectedRfpId ? planByRfp.get(selectedRfpId) : undefined;

  const { data: details } = useCaptureDetails(selectedRfpId, selectedPlan?.id);

  const partnerLinks = details?.partnerLinks ?? [];
  const gateReviews = details?.gateReviews ?? [];
  const planFieldValues = details?.planFieldValues ?? [];
  const selectedRfp = details?.selectedRfp ?? null;
  const competitors = details?.competitors ?? [];
  const matchInsight = details?.matchInsight ?? null;

  const refreshData = () => queryClient.invalidateQueries({ queryKey: ["capture-data"] });
  const refreshDetails = () =>
    queryClient.invalidateQueries({ queryKey: ["capture-details", selectedRfpId] });

  const handleCreatePlan = async (rfpId: number) => {
    try {
      await createPlan.mutateAsync({ rfp_id: rfpId });
    } catch {
      setError("Failed to create capture plan.");
    }
  };

  const handleUpdatePlan = async (
    planId: number,
    updates: Partial<{ stage: CaptureStage; bid_decision: import("@/types").BidDecision }>
  ) => {
    try {
      await updatePlan.mutateAsync({ planId, updates });
    } catch {
      setError("Failed to update capture plan.");
    }
  };

  if ((fetchError || error) && !isLoading) {
    return (
      <div className="flex flex-col h-full">
        <Header
          title="Capture"
          description="Track bid decisions, gate reviews, and teaming partners"
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-destructive mb-4">{error || "Failed to load capture data."}</p>
            <Button onClick={refreshData}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Capture"
        description="Track bid decisions, gate reviews, and teaming partners"
      />

      <div className="flex-1 p-6 overflow-hidden">
        <CaptureSummaryCards
          totalOpportunities={rfps.length}
          capturePlans={plans.length}
          pendingDecisions={plans.filter((p) => p.bid_decision === "pending").length}
        />

        <CapturePipeline
          rfps={rfps}
          planByRfp={planByRfp}
          plansByStage={plansByStage}
          onCreatePlan={handleCreatePlan}
          onUpdatePlan={handleUpdatePlan}
        />

        <div className="grid grid-cols-2 gap-6 mt-6">
          <GateReviewsPanel
            rfps={rfps}
            selectedRfpId={selectedRfpId}
            gateReviews={gateReviews}
            onSelectRfp={setSelectedRfpId}
            onGateReviewsChange={() => refreshDetails()}
            onError={setError}
          />
          <TeamingPartnersPanel
            rfps={rfps}
            partners={partners}
            partnerLinks={partnerLinks}
            selectedRfpId={selectedRfpId}
            onSelectRfp={setSelectedRfpId}
            onPartnerLinksChange={() => refreshDetails()}
            onPartnersRefresh={refreshData}
            onError={setError}
          />
        </div>

        <CompetitorTrackingPanel
          selectedRfp={selectedRfp}
          competitors={competitors}
          matchInsight={matchInsight}
          selectedRfpId={selectedRfpId}
          onCompetitorsChange={() => refreshDetails()}
          onError={setError}
        />

        {selectedRfpId && (
          <div className="bg-card border border-border rounded-lg p-4 mt-6">
            <BidScorecardPanel rfpId={selectedRfpId} />
          </div>
        )}

        <CustomFieldsPanel
          plan={selectedPlan}
          planFieldValues={planFieldValues}
          onFieldValuesChange={() => refreshDetails()}
          onFieldsChange={() => refreshData()}
          onError={setError}
        />
      </div>
    </div>
  );
}
