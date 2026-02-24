"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EventAlert } from "@/types";

interface EventAlertsProps {
  alerts: EventAlert[];
}

export function EventAlerts({ alerts }: EventAlertsProps) {
  return (
    <Card data-testid="events-alerts-card">
      <CardHeader>
        <CardTitle>
          Relevant Event Alerts <Badge variant="secondary">{alerts.length}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {alerts.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No high-confidence event alerts yet. Add agency and keyword preferences in Signals
            subscription settings to improve matching.
          </p>
        ) : (
          <div className="space-y-3">
            {alerts.slice(0, 6).map((alert) => (
              <div
                key={alert.event.id}
                className="rounded-lg border p-3"
                data-testid="event-alert-row"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{alert.event.title}</p>
                  <Badge variant="outline">{Math.round(alert.relevance_score)}%</Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  In {alert.days_until_event} day(s) • {alert.match_reasons.join(" • ")}
                </p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
