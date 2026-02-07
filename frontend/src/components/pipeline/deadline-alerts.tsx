"use client";

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { GanttPlanRow } from "@/types";

interface DeadlineAlertsProps {
  data: GanttPlanRow[];
}

export function DeadlineAlerts({ data }: DeadlineAlertsProps) {
  const alerts = useMemo(() => {
    const now = new Date();
    const items: Array<{
      rfpTitle: string;
      label: string;
      date: string;
      daysUntil: number;
      type: "overdue" | "approaching" | "upcoming";
    }> = [];

    for (const row of data) {
      // Check response deadline
      if (row.response_deadline) {
        const d = new Date(row.response_deadline);
        const days = Math.ceil((d.getTime() - now.getTime()) / 86_400_000);
        if (days <= 30) {
          items.push({
            rfpTitle: row.rfp_title,
            label: "Response Deadline",
            date: row.response_deadline.split("T")[0],
            daysUntil: days,
            type: days < 0 ? "overdue" : days <= 7 ? "approaching" : "upcoming",
          });
        }
      }

      // Check activity end dates
      for (const act of row.activities) {
        if (act.end_date && act.status !== "completed") {
          const d = new Date(act.end_date);
          const days = Math.ceil((d.getTime() - now.getTime()) / 86_400_000);
          if (days <= 14) {
            items.push({
              rfpTitle: row.rfp_title,
              label: act.title,
              date: act.end_date,
              daysUntil: days,
              type: days < 0 ? "overdue" : days <= 3 ? "approaching" : "upcoming",
            });
          }
        }
      }
    }

    return items.sort((a, b) => a.daysUntil - b.daysUntil);
  }, [data]);

  if (alerts.length === 0) return null;

  const badgeVariant = (type: string) => {
    if (type === "overdue") return "destructive" as const;
    if (type === "approaching") return "default" as const;
    return "secondary" as const;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upcoming Deadlines</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {alerts.slice(0, 10).map((alert, i) => (
            <div key={i} className="flex items-center justify-between text-sm">
              <div>
                <p className="font-medium">{alert.label}</p>
                <p className="text-xs text-muted-foreground">{alert.rfpTitle}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">{alert.date}</span>
                <Badge variant={badgeVariant(alert.type)}>
                  {alert.daysUntil < 0
                    ? `${Math.abs(alert.daysUntil)}d overdue`
                    : alert.daysUntil === 0
                      ? "Today"
                      : `${alert.daysUntil}d`}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
