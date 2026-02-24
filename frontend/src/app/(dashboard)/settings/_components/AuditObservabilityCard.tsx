"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { AuditEvent, AuditSummary, ObservabilityMetrics } from "@/types";

interface AuditObservabilityCardProps {
  auditSummary: AuditSummary | null;
  auditEvents: AuditEvent[];
  observability: ObservabilityMetrics | null;
}

export function AuditObservabilityCard({
  auditSummary,
  auditEvents,
  observability,
}: AuditObservabilityCardProps) {
  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Audit & Observability</p>
            <p className="text-xs text-muted-foreground">
              Operational health and compliance reporting
            </p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 text-sm">
          <div className="rounded-md border border-border px-3 py-2">
            <p className="text-xs text-muted-foreground">Audit Events (30d)</p>
            <p className="text-lg font-semibold">
              {auditSummary?.total_events ?? "--"}
            </p>
          </div>
          <div className="rounded-md border border-border px-3 py-2">
            <p className="text-xs text-muted-foreground">Sync Successes (30d)</p>
            <p className="text-lg font-semibold">
              {observability?.integration_syncs.success ?? "--"}
            </p>
          </div>
          <div className="rounded-md border border-border px-3 py-2">
            <p className="text-xs text-muted-foreground">Webhook Events (30d)</p>
            <p className="text-lg font-semibold">
              {observability?.webhook_events.total ?? "--"}
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">Recent audit activity</p>
          {auditEvents.length === 0 ? (
            <p className="text-sm text-muted-foreground">No audit events yet.</p>
          ) : (
            <div className="space-y-2">
              {auditEvents.map((event) => (
                <div
                  key={event.id}
                  className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                >
                  <div>
                    <p className="font-medium text-foreground">{event.action}</p>
                    <p className="text-xs text-muted-foreground">
                      {event.entity_type} · {new Date(event.created_at).toLocaleString()}
                    </p>
                  </div>
                  <Badge variant="outline">{event.entity_type}</Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
