"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Trophy, TrendingDown } from "lucide-react";
import type { WinRateData } from "@/types";

interface WinRateCardProps {
  data: WinRateData | null;
  loading: boolean;
}

export function WinRateCard({ data, loading }: WinRateCardProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="h-10 bg-muted rounded w-24" />
            <div className="h-4 bg-muted rounded w-32" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const winRate = data?.win_rate ?? 0;
  const totalWon = data?.total_won ?? 0;
  const totalLost = data?.total_lost ?? 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
        <Trophy className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold text-primary">{winRate}%</div>
        <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Trophy className="h-3 w-3 text-green-500" />
            {totalWon} won
          </span>
          <span className="flex items-center gap-1">
            <TrendingDown className="h-3 w-3 text-red-500" />
            {totalLost} lost
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
