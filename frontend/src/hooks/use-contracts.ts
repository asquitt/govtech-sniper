"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { contractApi, documentApi } from "@/lib/api";
import type {
  ContractAward,
  ContractDeliverable,
  ContractTask,
  CPARSReview,
  CPARSEvidence,
  ContractStatusReport,
  ContractModification,
  ContractCLIN,
  KnowledgeBaseDocument,
} from "@/types";

/**
 * Hook for fetching contract list
 */
export function useContracts() {
  return useQuery({
    queryKey: ["contracts"],
    queryFn: () => contractApi.list(),
  });
}

/**
 * Hook for fetching ready documents for contract linking
 */
export function useContractDocuments() {
  return useQuery({
    queryKey: ["contract-documents"],
    queryFn: () => documentApi.list({ ready_only: true }),
  });
}

/**
 * Hook for fetching all contract detail sub-resources in parallel
 */
export function useContractDetails(contractId: number | null) {
  return useQuery({
    queryKey: ["contract-details", contractId],
    queryFn: async () => {
      const [deliverables, tasks, modifications, clins, cpars, statusReports] =
        await Promise.all([
          contractApi.listDeliverables(contractId!),
          contractApi.listTasks(contractId!),
          contractApi.listModifications(contractId!),
          contractApi.listCLINs(contractId!),
          contractApi.listCPARS(contractId!),
          contractApi.listStatusReports(contractId!),
        ]);
      return { deliverables, tasks, modifications, clins, cpars, statusReports };
    },
    enabled: !!contractId,
  });
}

/**
 * Hook for fetching CPARS evidence items
 */
export function useCPARSEvidence(
  contractId: number | null,
  cparsId: number | null
) {
  return useQuery({
    queryKey: ["cpars-evidence", contractId, cparsId],
    queryFn: () => contractApi.listCPARSEvidence(contractId!, cparsId!),
    enabled: !!contractId && !!cparsId,
  });
}

/**
 * Hook for creating a new contract
 */
export function useCreateContract() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: Parameters<typeof contractApi.create>[0]) =>
      contractApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contracts"] });
    },
  });
}
