"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { signalApi } from "@/lib/api";
import type { SignalType, SignalCreatePayload, SubscriptionPayload } from "@/types/signals";

export function useSignalFeed(params?: {
  signal_type?: SignalType;
  unread_only?: boolean;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ["signal-feed", params],
    queryFn: () => signalApi.feed(params),
  });
}

export function useSignalSubscription() {
  return useQuery({
    queryKey: ["signal-subscription"],
    queryFn: () => signalApi.getSubscription(),
  });
}

export function useCreateSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SignalCreatePayload) => signalApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signal-feed"] });
    },
  });
}

export function useMarkSignalRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (signalId: number) => signalApi.markRead(signalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signal-feed"] });
    },
  });
}

export function useDeleteSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (signalId: number) => signalApi.delete(signalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signal-feed"] });
    },
  });
}

export function useUpsertSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SubscriptionPayload) => signalApi.upsertSubscription(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["signal-subscription"] });
    },
  });
}
