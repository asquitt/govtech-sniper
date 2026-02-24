"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ComplianceCheckpointSignoff } from "@/types/compliance";

export interface AssessorSignoffCardProps {
  signoff: ComplianceCheckpointSignoff | null;
  canManage: boolean;
  isSavingSignoff: boolean;
  selectedCheckpointId: string;
  onSignoffChange: (updater: (prev: ComplianceCheckpointSignoff | null) => ComplianceCheckpointSignoff | null) => void;
  onSave: (event: React.FormEvent) => void;
}

export function AssessorSignoffCard({
  signoff,
  canManage,
  isSavingSignoff,
  selectedCheckpointId,
  onSignoffChange,
  onSave,
}: AssessorSignoffCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Assessor Sign-Off</CardTitle>
      </CardHeader>
      <CardContent>
        {signoff ? (
          <form className="space-y-3" onSubmit={onSave}>
            <div className="grid gap-3 md:grid-cols-2">
              <select
                aria-label="Sign-off status"
                className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={signoff.status}
                onChange={(event) =>
                  onSignoffChange((prev) =>
                    prev
                      ? {
                          ...prev,
                          status: event.target.value as
                            | "pending"
                            | "approved"
                            | "rejected",
                        }
                      : prev
                  )
                }
                disabled={!canManage || isSavingSignoff}
              >
                <option value="pending">pending</option>
                <option value="approved">approved</option>
                <option value="rejected">rejected</option>
              </select>
              <input
                aria-label="Assessor name"
                className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={signoff.assessor_name}
                onChange={(event) =>
                  onSignoffChange((prev) =>
                    prev ? { ...prev, assessor_name: event.target.value } : prev
                  )
                }
                disabled={!canManage || isSavingSignoff}
              />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <input
                aria-label="Assessor organization"
                className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={signoff.assessor_org ?? ""}
                onChange={(event) =>
                  onSignoffChange((prev) =>
                    prev ? { ...prev, assessor_org: event.target.value } : prev
                  )
                }
                placeholder="Assessor organization"
                disabled={!canManage || isSavingSignoff}
              />
              <input
                aria-label="Sign-off notes"
                className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={signoff.notes ?? ""}
                onChange={(event) =>
                  onSignoffChange((prev) =>
                    prev ? { ...prev, notes: event.target.value } : prev
                  )
                }
                placeholder="Notes"
                disabled={!canManage || isSavingSignoff}
              />
            </div>
            {canManage ? (
              <Button type="submit" disabled={isSavingSignoff || !selectedCheckpointId}>
                {isSavingSignoff ? "Saving..." : "Save Sign-Off"}
              </Button>
            ) : null}
          </form>
        ) : (
          <p className="text-sm text-muted-foreground">No sign-off data loaded.</p>
        )}
      </CardContent>
    </Card>
  );
}
