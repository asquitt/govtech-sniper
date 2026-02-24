"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { reviewApi } from "@/lib/api";
import type { ReviewDashboardItem, ReviewPacket, ReviewType, ReviewStatus } from "@/types";
import { ClipboardCheck } from "lucide-react";
import { ReviewCard } from "./_components/review-card";
import { ReviewStatsCards } from "./_components/review-stats-cards";
import { ReviewPacketBuilder } from "./_components/review-packet-builder";

export default function ReviewsPage() {
  const [items, setItems] = useState<ReviewDashboardItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterType, setFilterType] = useState<ReviewType | "all">("all");
  const [filterStatus, setFilterStatus] = useState<ReviewStatus | "all">("all");
  const [selectedReviewId, setSelectedReviewId] = useState<number | null>(null);
  const [packet, setPacket] = useState<ReviewPacket | null>(null);
  const [isPacketLoading, setIsPacketLoading] = useState(false);
  const [packetError, setPacketError] = useState<string | null>(null);
  const [now] = useState(() => Date.now());

  const fetchDashboard = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await reviewApi.getDashboard();
      setItems(data);
      setSelectedReviewId((existing) => {
        if (existing && data.some((item) => item.review_id === existing)) {
          return existing;
        }
        return data[0]?.review_id ?? null;
      });
    } catch (err) {
      console.error("Failed to load review dashboard", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const fetchPacket = useCallback(async (reviewId: number) => {
    try {
      setPacketError(null);
      setIsPacketLoading(true);
      const response = await reviewApi.getReviewPacket(reviewId);
      setPacket(response);
    } catch (err) {
      console.error("Failed to load review packet", err);
      setPacket(null);
      setPacketError("Failed to load review packet.");
    } finally {
      setIsPacketLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedReviewId) {
      setPacket(null);
      return;
    }
    fetchPacket(selectedReviewId);
  }, [selectedReviewId, fetchPacket]);

  const filtered = items.filter((item) => {
    if (filterType !== "all" && item.review_type !== filterType) return false;
    if (filterStatus !== "all" && item.status !== filterStatus) return false;
    return true;
  });

  return (
    <div className="flex flex-col h-full">
      <Header title="Review Dashboard" />
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Filters */}
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            {(["all", "pink", "red", "gold"] as const).map((t) => (
              <Button
                key={t}
                size="sm"
                variant={filterType === t ? "default" : "outline"}
                onClick={() => setFilterType(t)}
              >
                {t === "all" ? "All Types" : `${t.toUpperCase()} Team`}
              </Button>
            ))}
          </div>
          <div className="flex gap-1">
            {(
              ["all", "scheduled", "in_progress", "completed"] as const
            ).map((s) => (
              <Button
                key={s}
                size="sm"
                variant={filterStatus === s ? "default" : "outline"}
                onClick={() => setFilterStatus(s)}
              >
                {s === "all"
                  ? "All Status"
                  : s.replace("_", " ").replace(/\b\w/g, (c) =>
                      c.toUpperCase()
                    )}
              </Button>
            ))}
          </div>
        </div>

        <ReviewStatsCards items={items} />

        <ReviewPacketBuilder
          items={items}
          selectedReviewId={selectedReviewId}
          packet={packet}
          isPacketLoading={isPacketLoading}
          packetError={packetError}
          onSelectReview={setSelectedReviewId}
          onRefresh={() => selectedReviewId && fetchPacket(selectedReviewId)}
        />

        {/* Review list */}
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <ClipboardCheck className="w-6 h-6 animate-pulse text-muted-foreground" />
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-12">
            No reviews found. Schedule a review from a proposal page.
          </p>
        ) : (
          <div className="space-y-3">
            {filtered.map((item) => (
              <ReviewCard key={item.review_id} item={item} now={now} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
