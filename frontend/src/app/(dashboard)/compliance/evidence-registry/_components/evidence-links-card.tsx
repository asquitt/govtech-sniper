"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type {
  ComplianceCheckpointEvidenceItem,
  ComplianceRegistryEvidenceItem,
} from "@/types/compliance";

export interface EvidenceLinksCardProps {
  evidenceItems: ComplianceCheckpointEvidenceItem[];
  registryEvidence: ComplianceRegistryEvidenceItem[];
  registryEvidenceScope: "mine" | "organization";
  selectedRegistryEvidenceId: string;
  linkEvidenceNotes: string;
  isLinking: boolean;
  isUpdatingStatusId: number | null;
  canManage: boolean;
  selectedCheckpointId: string;
  onScopeChange: (scope: "mine" | "organization") => void;
  onRefreshCatalog: () => void;
  onSelectedEvidenceChange: (id: string) => void;
  onNotesChange: (notes: string) => void;
  onLinkEvidence: (event: React.FormEvent) => void;
  onUpdateStatus: (linkId: number, status: "submitted" | "accepted" | "rejected") => void;
}

export function EvidenceLinksCard({
  evidenceItems,
  registryEvidence,
  registryEvidenceScope,
  selectedRegistryEvidenceId,
  linkEvidenceNotes,
  isLinking,
  isUpdatingStatusId,
  canManage,
  selectedCheckpointId,
  onScopeChange,
  onRefreshCatalog,
  onSelectedEvidenceChange,
  onNotesChange,
  onLinkEvidence,
  onUpdateStatus,
}: EvidenceLinksCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Evidence Links</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs text-muted-foreground">Evidence scope</label>
          <select
            aria-label="Evidence scope"
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            value={registryEvidenceScope}
            onChange={(event) =>
              onScopeChange(event.target.value as "mine" | "organization")
            }
          >
            <option value="organization">organization</option>
            <option value="mine">mine</option>
          </select>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={onRefreshCatalog}
          >
            Refresh Catalog
          </Button>
        </div>
        {canManage ? (
          <form className="grid gap-2 md:grid-cols-3" onSubmit={onLinkEvidence}>
            <select
              aria-label="Evidence catalog selection"
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={selectedRegistryEvidenceId}
              onChange={(event) => onSelectedEvidenceChange(event.target.value)}
            >
              {registryEvidence.length === 0 ? (
                <option value="">No evidence artifacts found</option>
              ) : null}
              {registryEvidence.map((item) => (
                <option key={item.id} value={item.id}>
                  #{item.id} · {item.title} ({item.evidence_type})
                </option>
              ))}
            </select>
            <input
              aria-label="Evidence notes"
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={linkEvidenceNotes}
              onChange={(event) => onNotesChange(event.target.value)}
              placeholder="Notes (optional)"
            />
            <Button
              type="submit"
              disabled={
                isLinking || !selectedCheckpointId || !selectedRegistryEvidenceId
              }
            >
              {isLinking ? "Linking..." : "Link Evidence"}
            </Button>
          </form>
        ) : (
          <p className="text-xs text-muted-foreground">
            Read-only: org owners/admins can link evidence and update statuses.
          </p>
        )}

        {evidenceItems.length === 0 ? (
          <p className="text-sm text-muted-foreground">No linked evidence for this checkpoint.</p>
        ) : (
          evidenceItems.map((item) => (
            <div key={item.link_id} className="rounded-lg border border-border p-3 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium">{item.title}</p>
                <Badge variant="outline">{item.status}</Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Evidence #{item.evidence_id} · Type {item.evidence_type}
              </p>
              {item.reviewer_notes ? (
                <p className="text-xs text-muted-foreground">Reviewer notes: {item.reviewer_notes}</p>
              ) : null}
              {canManage ? (
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={isUpdatingStatusId === item.link_id}
                    onClick={() => onUpdateStatus(item.link_id, "submitted")}
                  >
                    Mark Submitted
                  </Button>
                  <Button
                    size="sm"
                    disabled={isUpdatingStatusId === item.link_id}
                    onClick={() => onUpdateStatus(item.link_id, "accepted")}
                  >
                    Accept
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    disabled={isUpdatingStatusId === item.link_id}
                    onClick={() => onUpdateStatus(item.link_id, "rejected")}
                  >
                    Reject
                  </Button>
                </div>
              ) : null}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
