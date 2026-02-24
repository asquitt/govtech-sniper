"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type {
  WebSocketDiagnosticsAlertSnapshot,
  WebSocketDiagnosticsSnapshot,
  WebSocketDiagnosticsThresholds,
} from "@/types";

interface WebSocketTaskFeedProps {
  socketStatus: string;
  statusVariant: "success" | "secondary" | "destructive" | "outline";
  lastMessageType: string;
  lastTaskStatus: string;
  presenceCount: number;
  lockCount: number;
  cursorCount: number;
  diagnosticsTaskId: string;
  telemetry: WebSocketDiagnosticsSnapshot | null;
  manualReconnects: number;
  alertThresholds: WebSocketDiagnosticsThresholds;
  onAlertThresholdsChange: (thresholds: WebSocketDiagnosticsThresholds) => void;
  alertSnapshot: WebSocketDiagnosticsAlertSnapshot | null;
  isEvaluatingAlerts: boolean;
  isExportingTelemetry: boolean;
  onEvaluateAlerts: () => void;
  onExportTelemetry: () => void;
}

export function WebSocketTaskFeed({
  socketStatus,
  statusVariant,
  lastMessageType,
  lastTaskStatus,
  presenceCount,
  lockCount,
  cursorCount,
  diagnosticsTaskId,
  telemetry,
  manualReconnects,
  alertThresholds,
  onAlertThresholdsChange,
  alertSnapshot,
  isEvaluatingAlerts,
  isExportingTelemetry,
  onEvaluateAlerts,
  onExportTelemetry,
}: WebSocketTaskFeedProps) {
  return (
    <Card className="border border-border">
      <CardHeader>
        <CardTitle>WebSocket Task Feed</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-sm">
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">Connection status</p>
            <Badge className="mt-1" variant={statusVariant}>
              {socketStatus}
            </Badge>
          </div>
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">Last message</p>
            <p className="mt-1 font-medium">{lastMessageType}</p>
          </div>
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">Task status</p>
            <p className="mt-1 font-medium">{lastTaskStatus}</p>
          </div>
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">Presence telemetry</p>
            <p className="mt-1 font-medium">
              {presenceCount} users / {lockCount} locks / {cursorCount} cursors
            </p>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Active probe task id: <span className="font-mono">{diagnosticsTaskId}</span>
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">Task-watch latency</p>
            <p className="mt-1 font-medium" data-testid="telemetry-task-latency">
              {telemetry?.task_watch.avg_status_latency_ms != null
                ? `${telemetry.task_watch.avg_status_latency_ms}ms avg / ${telemetry.task_watch.p95_status_latency_ms ?? "n/a"}ms p95`
                : "n/a"}
            </p>
          </div>
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">Reconnect counts</p>
            <p className="mt-1 font-medium" data-testid="telemetry-reconnect-count">
              server {telemetry?.connections.reconnect_count ?? 0} / local{" "}
              {manualReconnects}
            </p>
          </div>
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">Event throughput</p>
            <p className="mt-1 font-medium" data-testid="telemetry-throughput">
              in {telemetry?.event_throughput.inbound_events_per_minute ?? 0}/min, out{" "}
              {telemetry?.event_throughput.outbound_events_per_minute ?? 0}/min
            </p>
          </div>
        </div>
        <div className="rounded-md border border-border p-3 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium text-foreground">
              Alert Threshold Evaluation
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={isEvaluatingAlerts}
                onClick={onEvaluateAlerts}
              >
                Evaluate Alerts
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={isExportingTelemetry}
                onClick={onExportTelemetry}
                data-testid="diagnostics-export-telemetry"
              >
                Export Telemetry CSV
              </Button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs md:grid-cols-3">
            <label className="space-y-1 text-muted-foreground">
              Max avg latency (ms)
              <input
                aria-label="Max avg latency threshold"
                type="number"
                className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                value={alertThresholds.max_avg_status_latency_ms}
                onChange={(event) =>
                  onAlertThresholdsChange({
                    ...alertThresholds,
                    max_avg_status_latency_ms:
                      Number.parseFloat(event.target.value) || 0,
                  })
                }
              />
            </label>
            <label className="space-y-1 text-muted-foreground">
              Max reconnects
              <input
                aria-label="Max reconnect threshold"
                type="number"
                className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                value={alertThresholds.max_reconnect_count}
                onChange={(event) =>
                  onAlertThresholdsChange({
                    ...alertThresholds,
                    max_reconnect_count:
                      Number.parseInt(event.target.value, 10) || 0,
                  })
                }
              />
            </label>
            <label className="space-y-1 text-muted-foreground">
              Min active connections
              <input
                aria-label="Min active connection threshold"
                type="number"
                className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                value={alertThresholds.min_active_connection_count}
                onChange={(event) =>
                  onAlertThresholdsChange({
                    ...alertThresholds,
                    min_active_connection_count:
                      Number.parseInt(event.target.value, 10) || 0,
                  })
                }
              />
            </label>
          </div>
          <p
            className="text-xs text-muted-foreground"
            data-testid="diagnostics-alert-count"
          >
            Breached alerts: {alertSnapshot?.breached_count ?? 0}
          </p>
          {alertSnapshot && alertSnapshot.alerts.length > 0 ? (
            <div className="space-y-1">
              {alertSnapshot.alerts
                .filter((alert) => alert.breached)
                .slice(0, 5)
                .map((alert) => (
                  <div
                    key={alert.code}
                    className="rounded border border-border/60 px-2 py-1 text-xs"
                    data-testid={`diagnostics-alert-${alert.code}`}
                  >
                    {alert.code}: {alert.metric} ({alert.actual} vs {alert.threshold})
                  </div>
                ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No active alert breaches.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
