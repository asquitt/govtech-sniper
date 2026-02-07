"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  TrendingDown,
  Lightbulb,
  AlertTriangle,
  Zap,
  Info,
} from "lucide-react";
import type { WinLossAnalysis, Recommendation } from "@/types";

interface WinLossCardProps {
  data: WinLossAnalysis | null;
  loading: boolean;
}

function RecommendationItem({ rec }: { rec: Recommendation }) {
  const iconMap = {
    strength: TrendingUp,
    warning: AlertTriangle,
    insight: Lightbulb,
    action: Zap,
  };
  const colorMap = {
    strength: "text-green-600",
    warning: "text-yellow-600",
    insight: "text-blue-600",
    action: "text-orange-600",
  };
  const Icon = iconMap[rec.type] || Info;
  const color = colorMap[rec.type] || "text-muted-foreground";

  return (
    <div className="flex gap-3 p-3 rounded-lg bg-muted/50">
      <Icon className={`h-4 w-4 mt-0.5 flex-shrink-0 ${color}`} />
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground">{rec.title}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{rec.message}</p>
      </div>
    </div>
  );
}

export function WinLossCard({ data, loading }: WinLossCardProps) {
  if (loading || !data) {
    return (
      <Card className="border border-border">
        <CardContent className="p-5">
          <div className="animate-pulse space-y-3">
            <div className="h-5 w-40 bg-muted rounded" />
            <div className="h-32 bg-muted rounded" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border border-border">
      <CardContent className="p-5 space-y-5">
        <p className="text-sm font-medium text-foreground">Win/Loss Analysis</p>

        {/* By Agency */}
        {data.by_agency.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-2">By Agency</p>
            <div className="space-y-1.5">
              {data.by_agency.slice(0, 8).map((a) => (
                <div key={a.agency} className="flex items-center justify-between text-sm">
                  <span className="text-foreground truncate max-w-[200px]">{a.agency}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {a.won}W/{a.lost}L
                    </span>
                    <Badge
                      variant={a.win_rate >= 50 ? "success" : a.win_rate >= 30 ? "warning" : "destructive"}
                      className="text-[10px] min-w-[42px] justify-center"
                    >
                      {a.win_rate}%
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* By Size */}
        {data.by_size.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-2">By Contract Size</p>
            <div className="space-y-1.5">
              {data.by_size.map((s) => (
                <div key={s.bucket} className="flex items-center justify-between text-sm">
                  <span className="text-foreground">{s.bucket}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {s.won}W/{s.lost}L
                    </span>
                    <Badge
                      variant={s.win_rate >= 50 ? "success" : s.win_rate >= 30 ? "warning" : "destructive"}
                      className="text-[10px] min-w-[42px] justify-center"
                    >
                      {s.win_rate}%
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Win Themes & Loss Factors */}
        <div className="grid grid-cols-2 gap-4">
          {data.top_win_themes.length > 0 && (
            <div>
              <p className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
                <TrendingUp className="h-3 w-3 text-green-600" /> Top Win Themes
              </p>
              <div className="space-y-1">
                {data.top_win_themes.slice(0, 5).map((t) => (
                  <div key={t.theme} className="flex items-center justify-between text-xs">
                    <span className="text-foreground truncate">{t.theme}</span>
                    <Badge variant="success" className="text-[10px]">{t.count}</Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
          {data.top_loss_factors.length > 0 && (
            <div>
              <p className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
                <TrendingDown className="h-3 w-3 text-red-600" /> Top Loss Factors
              </p>
              <div className="space-y-1">
                {data.top_loss_factors.slice(0, 5).map((f) => (
                  <div key={f.factor} className="flex items-center justify-between text-xs">
                    <span className="text-foreground truncate">{f.factor}</span>
                    <Badge variant="destructive" className="text-[10px]">{f.count}</Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Recommendations */}
        {data.recommendations.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-2">AI Recommendations</p>
            <div className="space-y-2">
              {data.recommendations.map((rec, i) => (
                <RecommendationItem key={i} rec={rec} />
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {data.by_agency.length === 0 && data.by_size.length === 0 && (
          <div className="text-center py-6 text-muted-foreground">
            <p className="text-sm">No win/loss data yet</p>
            <p className="text-xs mt-1">
              Mark opportunities as Won or Lost to see analysis
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
