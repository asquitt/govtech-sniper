"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import type { ReviewDashboardItem } from "@/types";

export interface ReviewStatsCardsProps {
  items: ReviewDashboardItem[];
}

export function ReviewStatsCards({ items }: ReviewStatsCardsProps) {
  return (
    <div className="grid grid-cols-4 gap-4">
      <Card>
        <CardContent className="pt-4 text-center">
          <p className="text-2xl font-bold">{items.length}</p>
          <p className="text-xs text-muted-foreground">Total Reviews</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4 text-center">
          <p className="text-2xl font-bold text-blue-500">
            {items.filter((i) => i.status === "in_progress").length}
          </p>
          <p className="text-xs text-muted-foreground">In Progress</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4 text-center">
          <p className="text-2xl font-bold text-yellow-500">
            {items.reduce((sum, i) => sum + i.open_comments, 0)}
          </p>
          <p className="text-xs text-muted-foreground">Open Comments</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4 text-center">
          <p className="text-2xl font-bold text-green-500">
            {items.filter((i) => i.status === "completed").length}
          </p>
          <p className="text-xs text-muted-foreground">Completed</p>
        </CardContent>
      </Card>
    </div>
  );
}
