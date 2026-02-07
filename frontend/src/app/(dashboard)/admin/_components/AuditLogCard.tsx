"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { OrgAuditEvent } from "@/types";

interface AuditLogCardProps {
  events: OrgAuditEvent[];
  loading: boolean;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

const ACTION_COLORS: Record<string, string> = {
  login: "bg-green-500/20 text-green-400",
  logout: "bg-gray-500/20 text-gray-400",
  create: "bg-blue-500/20 text-blue-400",
  update: "bg-amber-500/20 text-amber-400",
  delete: "bg-red-500/20 text-red-400",
};

function getActionColor(action: string): string {
  const key = Object.keys(ACTION_COLORS).find((k) => action.toLowerCase().includes(k));
  return key ? ACTION_COLORS[key] : "bg-muted text-muted-foreground";
}

export function AuditLogCard({ events, loading }: AuditLogCardProps) {
  if (loading) {
    return (
      <Card className="border border-border">
        <CardContent className="p-5">
          <div className="animate-pulse space-y-3">
            <div className="h-5 w-40 bg-muted rounded" />
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-8 bg-muted rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border border-border">
      <CardContent className="p-5 space-y-3">
        <p className="text-sm font-medium text-foreground">
          Organization Audit Log
        </p>

        <div className="space-y-1.5 max-h-[400px] overflow-y-auto">
          {events.map((event) => (
            <div
              key={event.id}
              className="flex items-center justify-between py-2 px-2 rounded text-xs hover:bg-muted/30"
            >
              <div className="flex items-center gap-2 min-w-0">
                <Badge className={`text-[9px] shrink-0 ${getActionColor(event.action)}`}>
                  {event.action}
                </Badge>
                <span className="text-muted-foreground truncate">
                  {event.user_email ?? "system"}
                </span>
                {event.entity_type && (
                  <span className="text-foreground">
                    {event.entity_type}
                    {event.entity_id ? ` #${event.entity_id}` : ""}
                  </span>
                )}
              </div>
              <span className="text-muted-foreground shrink-0 ml-2">
                {formatTime(event.created_at)}
              </span>
            </div>
          ))}

          {events.length === 0 && (
            <div className="text-center py-6 text-muted-foreground">
              <p className="text-sm">No audit events found</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
