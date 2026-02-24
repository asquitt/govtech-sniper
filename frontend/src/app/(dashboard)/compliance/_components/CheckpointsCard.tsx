"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ComplianceReadinessCheckpointSnapshot } from "@/types/compliance";

interface CheckpointsCardProps {
  readinessCheckpoints: ComplianceReadinessCheckpointSnapshot | null;
}

export function CheckpointsCard({ readinessCheckpoints }: CheckpointsCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Execution Checkpoints (FedRAMP, CMMC, GovCloud)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {readinessCheckpoints?.checkpoints.map((checkpoint) => (
          <div key={checkpoint.checkpoint_id} className="rounded-lg border border-border p-3 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium">{checkpoint.title}</p>
              <Badge variant="outline">{checkpoint.status.replaceAll("_", " ")}</Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Program: {checkpoint.program_id.replaceAll("_", " ")} · Target{" "}
              {new Date(checkpoint.target_date).toLocaleDateString()} · Owner: {checkpoint.owner}
            </p>
            <div className="h-2 rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary"
                style={{
                  width: `${
                    checkpoint.evidence_items_total > 0
                      ? Math.round(
                          (checkpoint.evidence_items_ready / checkpoint.evidence_items_total) * 100
                        )
                      : 0
                  }%`,
                }}
              />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={checkpoint.third_party_required ? "default" : "secondary"}>
                {checkpoint.third_party_required
                  ? "Third-party checkpoint"
                  : "Internal checkpoint"}
              </Badge>
              {checkpoint.evidence_source ? (
                <Badge variant="outline">
                  Source: {checkpoint.evidence_source}
                </Badge>
              ) : null}
              {checkpoint.assessor_signoff_status ? (
                <Badge
                  variant={
                    checkpoint.assessor_signoff_status === "approved"
                      ? "default"
                      : checkpoint.assessor_signoff_status === "rejected"
                        ? "destructive"
                        : "secondary"
                  }
                >
                  Assessor sign-off: {checkpoint.assessor_signoff_status}
                </Badge>
              ) : null}
              <p className="text-xs text-muted-foreground">
                Evidence {checkpoint.evidence_items_ready}/{checkpoint.evidence_items_total}
              </p>
              {checkpoint.evidence_last_updated_at ? (
                <p className="text-xs text-muted-foreground">
                  Updated {new Date(checkpoint.evidence_last_updated_at).toLocaleString()}
                </p>
              ) : null}
              {checkpoint.assessor_signoff_by ? (
                <p className="text-xs text-muted-foreground">
                  Assessor: {checkpoint.assessor_signoff_by}
                </p>
              ) : null}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
