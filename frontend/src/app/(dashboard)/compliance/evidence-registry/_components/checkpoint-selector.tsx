"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ComplianceReadinessCheckpoint } from "@/types/compliance";

export interface CheckpointSelectorProps {
  checkpoints: ComplianceReadinessCheckpoint[];
  selectedCheckpointId: string;
  onSelect: (id: string) => void;
}

export function CheckpointSelector({
  checkpoints,
  selectedCheckpointId,
  onSelect,
}: CheckpointSelectorProps) {
  const selectedCheckpoint = checkpoints.find(
    (checkpoint) => checkpoint.checkpoint_id === selectedCheckpointId
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Checkpoint</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <select
          aria-label="Readiness checkpoint"
          className="h-9 w-full max-w-xl rounded-md border border-input bg-background px-3 text-sm"
          value={selectedCheckpointId}
          onChange={(event) => onSelect(event.target.value)}
        >
          {checkpoints.map((checkpoint) => (
            <option key={checkpoint.checkpoint_id} value={checkpoint.checkpoint_id}>
              {checkpoint.title}
            </option>
          ))}
        </select>
        {selectedCheckpoint ? (
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline">{selectedCheckpoint.program_id.replaceAll("_", " ")}</Badge>
            {selectedCheckpoint.assessor_signoff_status ? (
              <Badge
                variant={
                  selectedCheckpoint.assessor_signoff_status === "approved"
                    ? "default"
                    : selectedCheckpoint.assessor_signoff_status === "rejected"
                      ? "destructive"
                      : "secondary"
                }
              >
                Sign-off: {selectedCheckpoint.assessor_signoff_status}
              </Badge>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
