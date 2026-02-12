"use client";

import Link from "next/link";
import React from "react";
import { Activity, Link2, Radio, Server, ShieldCheck } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AdminCapabilityHealth } from "@/types";

interface CapabilityHealthCardProps {
  capabilityHealth: AdminCapabilityHealth | null;
  loading: boolean;
}

function statusVariant(
  status: string
): "success" | "warning" | "outline" | "secondary" {
  if (status === "integrated" || status === "configured") {
    return "success";
  }
  if (status === "needs_configuration") {
    return "warning";
  }
  if (status === "ready") {
    return "secondary";
  }
  return "outline";
}

export function CapabilityHealthCard({
  capabilityHealth,
  loading,
}: CapabilityHealthCardProps) {
  if (loading || !capabilityHealth) {
    return (
      <Card className="border border-border">
        <CardContent className="p-5">
          <div className="animate-pulse space-y-3">
            <div className="h-5 w-44 bg-muted rounded" />
            <div className="h-24 bg-muted rounded" />
            <div className="h-20 bg-muted rounded" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const { workers, runtime, enterprise, integrations_by_provider, discoverability } =
    capabilityHealth;
  const taskModeLabel =
    workers.task_mode === "queued" ? "Queued workers" : "Sync fallback";

  return (
    <Card className="border border-border">
      <CardContent className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-foreground">Capability Health</p>
          <Badge variant={workers.task_mode === "queued" ? "success" : "warning"}>
            {taskModeLabel}
          </Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
          <div className="rounded-md border border-border px-3 py-2">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Server className="h-3.5 w-3.5" />
              Runtime
            </div>
            <p className="mt-1 text-foreground">
              {runtime.database_engine}
              <span className="text-xs text-muted-foreground ml-2">
                {runtime.mock_ai ? "MOCK_AI on" : "MOCK_AI off"}
              </span>
            </p>
          </div>
          <div className="rounded-md border border-border px-3 py-2">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Activity className="h-3.5 w-3.5" />
              Worker Reachability
            </div>
            <p className="mt-1 text-foreground">
              Broker {workers.broker_reachable ? "online" : "offline"} / Worker{" "}
              {workers.worker_online ? "online" : "offline"}
            </p>
          </div>
          <div className="rounded-md border border-border px-3 py-2">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <ShieldCheck className="h-3.5 w-3.5" />
              Enterprise Controls
            </div>
            <p className="mt-1 text-foreground">
              SCIM {enterprise.scim_configured ? "configured" : "not configured"}
            </p>
            <p className="text-xs text-muted-foreground">
              {enterprise.webhook_subscriptions} webhooks, {enterprise.stored_secrets} secrets
            </p>
          </div>
          <div className="rounded-md border border-border px-3 py-2">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Radio className="h-3.5 w-3.5" />
              WebSocket Feed
            </div>
            <p className="mt-1 text-foreground">
              {runtime.websocket.active_connections} active sockets
            </p>
            <p className="text-xs text-muted-foreground">
              {runtime.websocket.watched_tasks} watched tasks
            </p>
            <p className="text-xs text-muted-foreground">
              {runtime.websocket.active_documents} docs, {runtime.websocket.active_section_locks} locks,{" "}
              {runtime.websocket.active_cursors} cursors
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">Discoverability surfaces</p>
          <div className="space-y-2">
            {discoverability.map((item) => (
              <div
                key={item.capability}
                className="rounded-md border border-border px-3 py-2 text-xs space-y-1"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-foreground">{item.capability}</span>
                    <Badge variant={statusVariant(item.status)}>{item.status}</Badge>
                  </div>
                  {item.frontend_path ? (
                    <Link
                      href={item.frontend_path}
                      className="inline-flex items-center gap-1 text-primary hover:underline"
                    >
                      <Link2 className="h-3 w-3" />
                      {item.frontend_path}
                    </Link>
                  ) : (
                    <span className="text-muted-foreground">Backend only</span>
                  )}
                </div>
                <p className="text-muted-foreground">API: {item.backend_prefix}</p>
                <p className="text-muted-foreground">{item.note}</p>
              </div>
            ))}
          </div>
        </div>

        {integrations_by_provider.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">Integrations by provider</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {integrations_by_provider.map((item) => (
                <div key={item.provider} className="rounded-md border border-border px-2 py-2">
                  <p className="text-[11px] text-muted-foreground">{item.provider}</p>
                  <p className="text-sm font-semibold text-foreground">
                    {item.enabled}/{item.total}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
