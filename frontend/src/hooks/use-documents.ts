"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentApi } from "@/lib/api";
import type { KnowledgeBaseDocument } from "@/types";

/**
 * Hook for fetching documents list
 */
export function useDocuments(params?: {
  document_type?: string;
  ready_only?: boolean;
}) {
  return useQuery({
    queryKey: ["documents", params],
    queryFn: () => documentApi.list(params),
  });
}

/**
 * Hook for fetching single document
 */
export function useDocument(documentId: number) {
  return useQuery({
    queryKey: ["document", documentId],
    queryFn: () => documentApi.get(documentId),
    enabled: !!documentId,
  });
}

/**
 * Hook for fetching document types
 */
export function useDocumentTypes() {
  return useQuery({
    queryKey: ["document-types"],
    queryFn: () => documentApi.getTypes(),
    staleTime: Infinity, // These don't change
  });
}

/**
 * Hook for uploading document
 */
export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      file,
      metadata,
    }: {
      file: File;
      metadata: {
        title: string;
        document_type: string;
        description?: string;
      };
    }) => documentApi.upload(file, metadata),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

/**
 * Hook for updating document
 */
export function useUpdateDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      documentId,
      data,
    }: {
      documentId: number;
      data: Partial<KnowledgeBaseDocument>;
    }) => documentApi.update(documentId, data),
    onSuccess: (_, { documentId }) => {
      queryClient.invalidateQueries({ queryKey: ["document", documentId] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

/**
 * Hook for deleting document
 */
export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: number) => documentApi.delete(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

