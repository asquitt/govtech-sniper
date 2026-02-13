"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { collaborationApi } from "@/lib/api";

/**
 * Hook for fetching workspace list
 */
export function useWorkspaces() {
  return useQuery({
    queryKey: ["workspaces"],
    queryFn: () => collaborationApi.listWorkspaces(),
  });
}

/**
 * Hook for creating a workspace
 */
export function useCreateWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: collaborationApi.createWorkspace,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspaces"] });
    },
  });
}
