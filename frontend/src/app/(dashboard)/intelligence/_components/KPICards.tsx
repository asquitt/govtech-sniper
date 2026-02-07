"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import {
  Trophy,
  Target,
  DollarSign,
  FileText,
  Clock,
  AlertTriangle,
} from "lucide-react";
import type { KPIData } from "@/types";

interface KPICardsProps {
  data: KPIData | null;
  loading: boolean;
}

function formatCurrency(value: number): string {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function KPICard({
  icon: Icon,
  label,
  value,
  subtitle,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  subtitle?: string;
  color: string;
}) {
  return (
    <Card className="border border-border">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className={`rounded-lg p-2 ${color}`}>
            <Icon className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs text-muted-foreground truncate">{label}</p>
            <p className="text-xl font-bold text-foreground">{value}</p>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function KPICards({ data, loading }: KPICardsProps) {
  if (loading || !data) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="animate-pulse h-24 bg-muted rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <KPICard
        icon={Trophy}
        label="Win Rate"
        value={`${data.win_rate}%`}
        subtitle={`${data.total_won}W / ${data.total_lost}L`}
        color="bg-green-500/10 text-green-600"
      />
      <KPICard
        icon={DollarSign}
        label="Weighted Pipeline"
        value={formatCurrency(data.active_pipeline.weighted_value)}
        subtitle={`${data.active_pipeline.count} opportunities`}
        color="bg-blue-500/10 text-blue-600"
      />
      <KPICard
        icon={Target}
        label="Won Revenue"
        value={formatCurrency(data.won_revenue.value)}
        subtitle={`${data.won_revenue.count} active contracts`}
        color="bg-primary/10 text-primary"
      />
      <KPICard
        icon={FileText}
        label="Active Proposals"
        value={String(data.active_proposals)}
        subtitle={`${data.avg_turnaround_days}d avg turnaround`}
        color="bg-orange-500/10 text-orange-600"
      />
      <KPICard
        icon={DollarSign}
        label="Unweighted Pipeline"
        value={formatCurrency(data.active_pipeline.unweighted_value)}
        subtitle="Total face value"
        color="bg-indigo-500/10 text-indigo-600"
      />
      <KPICard
        icon={Clock}
        label="Avg Turnaround"
        value={`${data.avg_turnaround_days}d`}
        subtitle="RFP → Proposal (90d)"
        color="bg-yellow-500/10 text-yellow-600"
      />
      <KPICard
        icon={AlertTriangle}
        label="Upcoming Deadlines"
        value={String(data.upcoming_deadlines)}
        subtitle="Next 30 days"
        color="bg-red-500/10 text-red-600"
      />
      <KPICard
        icon={Trophy}
        label="Total Decided"
        value={String(data.total_won + data.total_lost)}
        subtitle={`${data.total_won} won`}
        color="bg-emerald-500/10 text-emerald-600"
      />
    </div>
  );
}
