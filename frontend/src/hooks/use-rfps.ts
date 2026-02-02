"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { rfpApi, analysisApi, ingestApi } from "@/lib/api";
import type { RFP, RFPListItem, ComplianceMatrix, SAMSearchParams } from "@/types";

/**
 * Hook for fetching RFP list
 */
export function useRFPs(params?: {
  status?: string;
  qualified_only?: boolean;
  skip?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["rfps", params],
    queryFn: () => rfpApi.list(params),
  });
}

/**
 * Hook for fetching single RFP
 */
export function useRFP(rfpId: number) {
  return useQuery({
    queryKey: ["rfp", rfpId],
    queryFn: () => rfpApi.get(rfpId),
    enabled: !!rfpId,
  });
}

/**
 * Hook for RFP stats
 */
export function useRFPStats() {
  return useQuery({
    queryKey: ["rfp-stats"],
    queryFn: () => rfpApi.getStats(),
  });
}

/**
 * Hook for fetching compliance matrix
 */
export function useComplianceMatrix(rfpId: number) {
  return useQuery({
    queryKey: ["compliance-matrix", rfpId],
    queryFn: () => analysisApi.getComplianceMatrix(rfpId),
    enabled: !!rfpId,
  });
}

/**
 * Hook for triggering SAM.gov ingest
 */
export function useSAMIngest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: SAMSearchParams) => ingestApi.triggerSamSearch(params),
    onSuccess: () => {
      // Invalidate RFP list after ingest
      queryClient.invalidateQueries({ queryKey: ["rfps"] });
      queryClient.invalidateQueries({ queryKey: ["rfp-stats"] });
    },
  });
}

/**
 * Hook for triggering RFP analysis
 */
export function useAnalyzeRFP() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ rfpId, forceReanalyze }: { rfpId: number; forceReanalyze?: boolean }) =>
      analysisApi.triggerAnalysis(rfpId, forceReanalyze),
    onSuccess: (_, { rfpId }) => {
      queryClient.invalidateQueries({ queryKey: ["rfp", rfpId] });
      queryClient.invalidateQueries({ queryKey: ["compliance-matrix", rfpId] });
    },
  });
}

/**
 * Hook for triggering Killer Filter
 */
export function useKillerFilter() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (rfpId: number) => analysisApi.triggerKillerFilter(rfpId),
    onSuccess: (_, rfpId) => {
      queryClient.invalidateQueries({ queryKey: ["rfp", rfpId] });
      queryClient.invalidateQueries({ queryKey: ["rfps"] });
    },
  });
}

/**
 * Hook for creating RFP
 */
export function useCreateRFP() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Partial<RFP>) => rfpApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rfps"] });
      queryClient.invalidateQueries({ queryKey: ["rfp-stats"] });
    },
  });
}

/**
 * Hook for updating RFP
 */
export function useUpdateRFP() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ rfpId, data }: { rfpId: number; data: Partial<RFP> }) =>
      rfpApi.update(rfpId, data),
    onSuccess: (_, { rfpId }) => {
      queryClient.invalidateQueries({ queryKey: ["rfp", rfpId] });
      queryClient.invalidateQueries({ queryKey: ["rfps"] });
    },
  });
}

/**
 * Hook for deleting RFP
 */
export function useDeleteRFP() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (rfpId: number) => rfpApi.delete(rfpId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rfps"] });
      queryClient.invalidateQueries({ queryKey: ["rfp-stats"] });
    },
  });
}

