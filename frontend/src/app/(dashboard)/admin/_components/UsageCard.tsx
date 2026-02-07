"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { BarChart2, FileText, Users, Activity } from "lucide-react";
import type { OrgUsageAnalytics } from "@/types";

interface UsageCardProps {
  usage: OrgUsageAnalytics | null;
  loading: boolean;
}

export function UsageCard({ usage, loading }: UsageCardProps) {
  if (loading || !usage) {
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

  const stats = [
    { icon: Users, label: "Active Users", value: usage.active_users, total: usage.members },
    { icon: FileText, label: "Proposals Created", value: usage.proposals },
    { icon: BarChart2, label: "RFPs Uploaded", value: usage.rfps },
    { icon: Activity, label: "Audit Events", value: usage.audit_events },
  ];

  return (
    <Card className="border border-border">
      <CardContent className="p-5 space-y-4">
        <p className="text-sm font-medium text-foreground">
          Usage Analytics ({usage.period_days}-day)
        </p>

        <div className="grid grid-cols-2 gap-3">
          {stats.map((stat) => (
            <div key={stat.label} className="p-3 rounded-lg bg-muted/30">
              <div className="flex items-center gap-1.5 mb-1">
                <stat.icon className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">{stat.label}</span>
              </div>
              <p className="text-xl font-bold text-foreground">
                {stat.value}
                {"total" in stat && stat.total !== undefined && (
                  <span className="text-xs font-normal text-muted-foreground ml-1">
                    / {stat.total}
                  </span>
                )}
              </p>
            </div>
          ))}
        </div>

        {/* Top actions */}
        {usage.by_action.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-2">Top Actions</p>
            <div className="space-y-1.5">
              {usage.by_action.slice(0, 6).map((item) => {
                const maxCount = usage.by_action[0]?.count ?? 1;
                const pct = Math.round((item.count / maxCount) * 100);
                return (
                  <div key={item.action} className="flex items-center gap-2">
                    <div className="flex-1">
                      <div className="flex items-center justify-between text-xs mb-0.5">
                        <span className="text-foreground">{item.action}</span>
                        <span className="text-muted-foreground">{item.count}</span>
                      </div>
                      <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
