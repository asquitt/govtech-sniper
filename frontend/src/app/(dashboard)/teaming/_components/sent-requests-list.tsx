"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TeamingRequest } from "@/types";

interface SentRequestsListProps {
  requests: TeamingRequest[];
  loading: boolean;
}

function statusBadgeVariant(status: string) {
  if (status === "accepted") return "default" as const;
  if (status === "declined") return "destructive" as const;
  return "secondary" as const;
}

export function SentRequestsList({ requests, loading }: SentRequestsListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Sent Requests</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="animate-pulse space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="h-16 bg-muted rounded" />
            ))}
          </div>
        ) : requests.length === 0 ? (
          <p className="text-muted-foreground text-sm text-center py-8">
            No sent requests yet.
          </p>
        ) : (
          <div className="space-y-3">
            {requests.map((r) => (
              <div key={r.id} className="border rounded-lg p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium">{r.partner_name || `Partner #${r.to_partner_id}`}</p>
                  {r.message && (
                    <p className="text-xs text-muted-foreground mt-1">{r.message}</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    Sent: {new Date(r.created_at).toLocaleDateString()}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Updated: {new Date(r.updated_at).toLocaleString()}
                  </p>
                </div>
                <Badge variant={statusBadgeVariant(r.status)}>{r.status}</Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
