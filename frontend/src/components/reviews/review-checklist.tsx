"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Check, X, Minus, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { reviewApi } from "@/lib/api";
import type { ReviewChecklistItem, ChecklistItemStatus } from "@/types";

const STATUS_CONFIG: Record<
  ChecklistItemStatus,
  { icon: React.ReactNode; label: string; color: string }
> = {
  pending: {
    icon: <Minus className="w-3.5 h-3.5" />,
    label: "Pending",
    color: "text-muted-foreground",
  },
  pass: {
    icon: <Check className="w-3.5 h-3.5" />,
    label: "Pass",
    color: "text-green-600",
  },
  fail: {
    icon: <X className="w-3.5 h-3.5" />,
    label: "Fail",
    color: "text-red-600",
  },
  na: {
    icon: <Minus className="w-3.5 h-3.5" />,
    label: "N/A",
    color: "text-muted-foreground",
  },
};

const STATUS_CYCLE: ChecklistItemStatus[] = ["pending", "pass", "fail", "na"];

interface ReviewChecklistProps {
  reviewId: number;
  reviewType: string;
}

export default function ReviewChecklist({
  reviewId,
  reviewType,
}: ReviewChecklistProps) {
  const [items, setItems] = useState<ReviewChecklistItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  const fetchChecklist = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await reviewApi.getChecklist(reviewId);
      setItems(data);
    } catch (err) {
      console.error("Failed to load checklist", err);
    } finally {
      setIsLoading(false);
    }
  }, [reviewId]);

  useEffect(() => {
    fetchChecklist();
  }, [fetchChecklist]);

  const handleCreateFromTemplate = async () => {
    try {
      setIsCreating(true);
      const data = await reviewApi.createChecklist(reviewId, {
        review_type: reviewType,
      });
      setItems(data);
    } catch (err) {
      console.error("Failed to create checklist", err);
    } finally {
      setIsCreating(false);
    }
  };

  const handleToggleStatus = async (item: ReviewChecklistItem) => {
    const currentIndex = STATUS_CYCLE.indexOf(item.status);
    const nextStatus = STATUS_CYCLE[(currentIndex + 1) % STATUS_CYCLE.length];
    try {
      const updated = await reviewApi.updateChecklistItem(reviewId, item.id, {
        status: nextStatus,
      });
      setItems((prev) => prev.map((i) => (i.id === item.id ? updated : i)));
    } catch (err) {
      console.error("Failed to update checklist item", err);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-24">
          <Loader2 className="w-5 h-5 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  if (items.length === 0) {
    return (
      <Card>
        <CardContent className="pt-4 text-center space-y-3">
          <p className="text-sm text-muted-foreground">
            No checklist items yet.
          </p>
          <Button
            onClick={handleCreateFromTemplate}
            disabled={isCreating}
            size="sm"
          >
            {isCreating && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
            Load {reviewType.toUpperCase()} Team Checklist
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Group by category
  const grouped = items.reduce<Record<string, ReviewChecklistItem[]>>(
    (acc, item) => {
      const key = item.category;
      if (!acc[key]) acc[key] = [];
      acc[key].push(item);
      return acc;
    },
    {}
  );

  const totalItems = items.length;
  const completedItems = items.filter(
    (i) => i.status === "pass" || i.status === "na"
  ).length;
  const progressPercent =
    totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">
            Review Checklist — {reviewType.toUpperCase()} Team
          </CardTitle>
          <span className="text-xs text-muted-foreground font-mono">
            {completedItems}/{totalItems} ({progressPercent}%)
          </span>
        </div>
        <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500 rounded-full transition-all"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {Object.entries(grouped).map(([category, categoryItems]) => (
          <div key={category}>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
              {category}
            </p>
            <div className="space-y-1">
              {categoryItems.map((item) => {
                const cfg = STATUS_CONFIG[item.status];
                return (
                  <button
                    key={item.id}
                    className="flex items-center gap-2 w-full text-left px-2 py-1.5 rounded hover:bg-secondary/50 transition-colors"
                    onClick={() => handleToggleStatus(item)}
                  >
                    <span
                      className={`flex-shrink-0 w-5 h-5 rounded border flex items-center justify-center ${cfg.color}`}
                    >
                      {cfg.icon}
                    </span>
                    <span
                      className={`text-sm flex-1 ${
                        item.status === "pass" || item.status === "na"
                          ? "line-through text-muted-foreground"
                          : "text-foreground"
                      }`}
                    >
                      {item.item_text}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
