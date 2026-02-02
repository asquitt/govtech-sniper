"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { draftApi } from "@/lib/api";
import type { DraftRequest, Proposal } from "@/types";

/**
 * Hook for creating a proposal
 */
export function useCreateProposal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ rfpId, title }: { rfpId: number; title: string }) =>
      draftApi.createProposal(rfpId, title),
    onSuccess: (_, { rfpId }) => {
      queryClient.invalidateQueries({ queryKey: ["proposals", rfpId] });
    },
  });
}

/**
 * Hook for generating sections from compliance matrix
 */
export function useGenerateFromMatrix() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (proposalId: number) => draftApi.generateFromMatrix(proposalId),
    onSuccess: (_, proposalId) => {
      queryClient.invalidateQueries({ queryKey: ["proposal", proposalId] });
      queryClient.invalidateQueries({ queryKey: ["proposal-sections", proposalId] });
    },
  });
}

/**
 * Hook for generating a single section
 */
export function useGenerateSection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      requirementId,
      request,
    }: {
      requirementId: string;
      request?: DraftRequest;
    }) => draftApi.generateSection(requirementId, request),
  });
}

/**
 * Hook for generating all sections
 */
export function useGenerateAllSections() {
  return useMutation({
    mutationFn: ({
      proposalId,
      options,
    }: {
      proposalId: number;
      options?: { max_words?: number; tone?: string };
    }) => draftApi.generateAllSections(proposalId, options),
  });
}

/**
 * Hook for refreshing context cache
 */
export function useRefreshCache() {
  return useMutation({
    mutationFn: (ttlHours?: number) => draftApi.refreshCache(ttlHours),
  });
}

/**
 * Hook for polling task status
 */
export function useTaskStatus(taskId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["task-status", taskId],
    queryFn: () => draftApi.getGenerationStatus(taskId!),
    enabled: !!taskId && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Stop polling when completed or failed
      if (status === "completed" || status === "failed") {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
  });
}

