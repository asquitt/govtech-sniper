"use client";

import React from "react";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { collaborationApi } from "@/lib/api";
import type { SharedDataPermission } from "@/types";

interface SharedDataListProps {
  workspaceId: number;
  sharedData: SharedDataPermission[];
  onDataChanged: () => Promise<void>;
}

function formatExpiration(expiresAt?: string | null) {
  if (!expiresAt) return "No expiry";
  const expiryDate = new Date(expiresAt);
  if (Number.isNaN(expiryDate.getTime())) return "No expiry";
  return `Expires ${expiryDate.toLocaleDateString()}`;
}

export function SharedDataList({
  workspaceId,
  sharedData,
  onDataChanged,
}: SharedDataListProps) {
  if (sharedData.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No data shared yet. Share RFP summaries, compliance matrices,
        contract feeds, or forecasts with workspace members.
      </p>
    );
  }

  return (
    <>
      {sharedData.map((sd) => (
        <div
          key={sd.id}
          data-testid={`shared-item-${sd.id}`}
          className="flex items-center justify-between gap-3 p-3 rounded-lg border border-border"
        >
          <div className="min-w-0 flex items-center gap-2">
            <Badge variant="outline">{sd.data_type.replace(/_/g, " ")}</Badge>
            <Badge variant={sd.approval_status === "approved" ? "default" : "secondary"}>
              {sd.approval_status}
            </Badge>
            <div className="min-w-0">
              <span className="block truncate text-sm text-muted-foreground">
                {sd.label || `Entity #${sd.entity_id}`}
              </span>
              <span className="block truncate text-[11px] text-muted-foreground">
                {sd.partner_user_id
                  ? `Scoped to user #${sd.partner_user_id}`
                  : "Visible to all members"}{" "}
                &middot; {formatExpiration(sd.expires_at)}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {sd.approval_status === "pending" && (
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  await collaborationApi.approveSharedData(workspaceId, sd.id);
                  await onDataChanged();
                }}
              >
                Approve
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={async () => {
                await collaborationApi.unshareData(workspaceId, sd.id);
                onDataChanged();
              }}
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
        </div>
      ))}
    </>
  );
}
