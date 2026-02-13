"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { captureApi, rfpApi } from "@/lib/api";
import type {
  CapturePlanListItem,
  TeamingPartner,
  CaptureCustomField,
  RFPListItem,
  CaptureStage,
  BidDecision,
} from "@/types";

/**
 * Fetches all 4 capture list endpoints in parallel (rfps, plans, partners, customFields).
 */
export function useCaptureData() {
  return useQuery({
    queryKey: ["capture-data"],
    queryFn: async () => {
      const [rfps, plans, partners, customFields] = await Promise.all([
        rfpApi.list({ limit: 100 }),
        captureApi.listPlans(),
        captureApi.listPartners(),
        captureApi.listFields(),
      ]);
      return {
        rfps: rfps as RFPListItem[],
        plans: plans as CapturePlanListItem[],
        partners: partners as TeamingPartner[],
        customFields: customFields as CaptureCustomField[],
      };
    },
  });
}

/**
 * Fetches detail data for a selected RFP: partner links, gate reviews,
 * plan field values, RFP detail, competitors, and match insight.
 */
export function useCaptureDetails(
  rfpId: number | null,
  planId: number | undefined
) {
  return useQuery({
    queryKey: ["capture-details", rfpId],
    queryFn: async () => {
      const [
        linksResult,
        gateReviews,
        fieldsResult,
        selectedRfp,
        competitors,
        matchInsight,
      ] = await Promise.all([
        captureApi.listPartnerLinks(rfpId!),
        captureApi.listGateReviews(rfpId!),
        planId
          ? captureApi.listPlanFields(planId)
          : Promise.resolve({ fields: [] }),
        rfpApi.get(rfpId!),
        captureApi.listCompetitors(rfpId!),
        planId
          ? captureApi.getMatchInsight(planId)
          : Promise.resolve(null),
      ]);
      return {
        partnerLinks: linksResult.links,
        gateReviews,
        planFieldValues: fieldsResult.fields ?? [],
        selectedRfp,
        competitors,
        matchInsight,
      };
    },
    enabled: !!rfpId,
  });
}

/**
 * Mutation for creating a capture plan. Invalidates capture-data on success.
 */
export function useCreateCapturePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: {
      rfp_id: number;
      stage?: CaptureStage;
      bid_decision?: BidDecision;
    }) => captureApi.createPlan(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["capture-data"] });
    },
  });
}

/**
 * Mutation for updating a capture plan. Invalidates capture-data on success.
 */
export function useUpdateCapturePlan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      planId,
      updates,
    }: {
      planId: number;
      updates: Partial<{ stage: CaptureStage; bid_decision: BidDecision }>;
    }) => captureApi.updatePlan(planId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["capture-data"] });
    },
  });
}
