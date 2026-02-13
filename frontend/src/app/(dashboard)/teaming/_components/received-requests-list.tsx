"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TeamingRequest } from "@/types";

interface ReceivedRequestsListProps {
  requests: TeamingRequest[];
  loading: boolean;
  onUpdateRequest: (requestId: number, status: "accepted" | "declined") => void;
}

function statusBadgeVariant(status: string) {
  if (status === "accepted") return "default" as const;
  if (status === "declined") return "destructive" as const;
  return "secondary" as const;
}

export function ReceivedRequestsList({
  requests,
  loading,
  onUpdateRequest,
}: ReceivedRequestsListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Received Requests</CardTitle>
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
            No received requests.
          </p>
        ) : (
          <div className="space-y-3">
            {requests.map((r) => (
              <div key={r.id} className="border rounded-lg p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium">
                    {r.from_user_name || r.from_user_email || `From User #${r.from_user_id}`}
                  </p>
                  {r.message && (
                    <p className="text-xs text-muted-foreground mt-1">{r.message}</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    Received: {new Date(r.created_at).toLocaleDateString()}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Updated: {new Date(r.updated_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={statusBadgeVariant(r.status)}>{r.status}</Badge>
                  {r.status === "pending" && (
                    <>
                      <Button
                        size="sm"
                        onClick={() => onUpdateRequest(r.id, "accepted")}
                      >
                        Accept
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onUpdateRequest(r.id, "declined")}
                      >
                        Decline
                      </Button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
