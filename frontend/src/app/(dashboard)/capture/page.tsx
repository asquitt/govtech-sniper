"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { captureApi, rfpApi } from "@/lib/api";
import BidScorecardPanel from "./_components/bid-scorecard-panel";
import { CaptureSummaryCards } from "./_components/capture-summary-cards";
import { CapturePipeline } from "./_components/capture-pipeline";
import { GateReviewsPanel } from "./_components/gate-reviews-panel";
import { TeamingPartnersPanel } from "./_components/teaming-partners-panel";
import { CompetitorTrackingPanel } from "./_components/competitor-tracking-panel";
import { CustomFieldsPanel } from "./_components/custom-fields-panel";
import type {
  CapturePlanListItem,
  CaptureStage,
  BidDecision,
  GateReview,
  TeamingPartner,
  TeamingPartnerLink,
  RFPListItem,
  RFP,
  CaptureCustomField,
  CaptureFieldValue,
  CaptureCompetitor,
  CaptureMatchInsight,
} from "@/types";

export default function CapturePage() {
  const [rfps, setRfps] = useState<RFPListItem[]>([]);
  const [plans, setPlans] = useState<CapturePlanListItem[]>([]);
  const [partners, setPartners] = useState<TeamingPartner[]>([]);
  const [partnerLinks, setPartnerLinks] = useState<TeamingPartnerLink[]>([]);
  const [gateReviews, setGateReviews] = useState<GateReview[]>([]);
  const [selectedRfpId, setSelectedRfpId] = useState<number | null>(null);
  const [selectedRfp, setSelectedRfp] = useState<RFP | null>(null);
  const [customFields, setCustomFields] = useState<CaptureCustomField[]>([]);
  const [planFieldValues, setPlanFieldValues] = useState<CaptureFieldValue[]>(
    []
  );
  const [matchInsight, setMatchInsight] =
    useState<CaptureMatchInsight | null>(null);
  const [competitors, setCompetitors] = useState<CaptureCompetitor[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [rfpList, planList, partnerList, fieldList] = await Promise.all([
        rfpApi.list({ limit: 100 }),
        captureApi.listPlans(),
        captureApi.listPartners(),
        captureApi.listFields(),
      ]);
      setRfps(rfpList);
      setPlans(planList);
      setPartners(partnerList);
      setCustomFields(fieldList);
      if (
        rfpList.length > 0 &&
        (selectedRfpId === null ||
          !rfpList.some((rfp) => rfp.id === selectedRfpId))
      ) {
        setSelectedRfpId(rfpList[0].id);
      }
    } catch (err) {
      console.error("Failed to load capture data", err);
      setError("Failed to load capture data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [selectedRfpId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const planByRfp = useMemo(() => {
    const map = new Map<number, CapturePlanListItem>();
    plans.forEach((plan) => map.set(plan.rfp_id, plan));
    return map;
  }, [plans]);

  const plansByStage = useMemo(() => {
    const stageValues: CaptureStage[] = [
      "identified",
      "qualified",
      "pursuit",
      "proposal",
      "submitted",
      "won",
      "lost",
    ];
    const map = new Map<CaptureStage, CapturePlanListItem[]>();
    stageValues.forEach((s) => map.set(s, []));
    plans.forEach((plan) => {
      const bucket = map.get(plan.stage);
      if (bucket) {
        bucket.push(plan);
      } else {
        map.set(plan.stage, [plan]);
      }
    });
    return map;
  }, [plans]);

  useEffect(() => {
    const fetchRfpDetails = async () => {
      if (!selectedRfpId) {
        setSelectedRfp(null);
        setMatchInsight(null);
        setCompetitors([]);
        return;
      }
      try {
        const plan = planByRfp.get(selectedRfpId);
        const [
          linksResult,
          reviewsResult,
          fieldsResult,
          rfpDetail,
          competitorList,
          insight,
        ] = await Promise.all([
          captureApi.listPartnerLinks(selectedRfpId),
          captureApi.listGateReviews(selectedRfpId),
          plan
            ? captureApi.listPlanFields(plan.id)
            : Promise.resolve({ fields: [] }),
          rfpApi.get(selectedRfpId),
          captureApi.listCompetitors(selectedRfpId),
          plan
            ? captureApi.getMatchInsight(plan.id)
            : Promise.resolve(null),
        ]);
        setPartnerLinks(linksResult.links);
        setGateReviews(reviewsResult);
        setPlanFieldValues(fieldsResult.fields ?? []);
        setSelectedRfp(rfpDetail);
        setCompetitors(competitorList);
        setMatchInsight(insight);
      } catch (err) {
        console.error("Failed to load capture details", err);
      }
    };
    fetchRfpDetails();
  }, [selectedRfpId, planByRfp]);

  const handleCreatePlan = async (rfpId: number) => {
    try {
      await captureApi.createPlan({ rfp_id: rfpId });
      await fetchData();
    } catch (err) {
      console.error("Failed to create capture plan", err);
      setError("Failed to create capture plan.");
    }
  };

  const handleUpdatePlan = async (
    planId: number,
    updates: Partial<{ stage: CaptureStage; bid_decision: BidDecision }>
  ) => {
    try {
      await captureApi.updatePlan(planId, updates);
      await fetchData();
    } catch (err) {
      console.error("Failed to update capture plan", err);
      setError("Failed to update capture plan.");
    }
  };

  if (error && !isLoading) {
    return (
      <div className="flex flex-col h-full">
        <Header
          title="Capture"
          description="Track bid decisions, gate reviews, and teaming partners"
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={fetchData}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

  const selectedPlan = selectedRfpId
    ? planByRfp.get(selectedRfpId)
    : undefined;

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
          pendingDecisions={
            plans.filter((p) => p.bid_decision === "pending").length
          }
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
            onGateReviewsChange={setGateReviews}
            onError={setError}
          />
          <TeamingPartnersPanel
            rfps={rfps}
            partners={partners}
            partnerLinks={partnerLinks}
            selectedRfpId={selectedRfpId}
            onSelectRfp={setSelectedRfpId}
            onPartnerLinksChange={setPartnerLinks}
            onPartnersRefresh={fetchData}
            onError={setError}
          />
        </div>

        <CompetitorTrackingPanel
          selectedRfp={selectedRfp}
          competitors={competitors}
          matchInsight={matchInsight}
          selectedRfpId={selectedRfpId}
          onCompetitorsChange={setCompetitors}
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
          onFieldValuesChange={setPlanFieldValues}
          onFieldsChange={setCustomFields}
          onError={setError}
        />
      </div>
    </div>
  );
}
