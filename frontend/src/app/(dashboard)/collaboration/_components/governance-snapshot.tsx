"use client";

import React from "react";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import type {
  GovernanceAnomaly,
  ShareGovernanceSummary,
  ShareGovernanceTrends,
} from "@/types";

interface GovernanceSnapshotProps {
  workspaceId: number;
  governanceSummary: ShareGovernanceSummary | null;
  governanceTrends: ShareGovernanceTrends | null;
  governanceAnomalies: GovernanceAnomaly[];
  isExportingAudit: boolean;
  onExportAudit: () => void;
}

export function GovernanceSnapshot({
  governanceSummary,
  governanceTrends,
  governanceAnomalies,
  isExportingAudit,
  onExportAudit,
}: GovernanceSnapshotProps) {
  const latestTrendPoints = (governanceTrends?.points ?? []).slice(-7).reverse();

  return (
    <>
      <div className="rounded-lg border border-border bg-card p-3">
        <div className="mb-2 flex flex-wrap items-end justify-between gap-2">
          <p className="text-sm font-medium text-foreground">Governance Snapshot</p>
          <div className="flex items-end gap-2">
            <Button
              variant="outline"
              size="sm"
              data-testid="export-governance-audit"
              disabled={isExportingAudit}
              onClick={onExportAudit}
            >
              <Download className="w-3.5 h-3.5" />
              Export Audit CSV
            </Button>
          </div>
        </div>
        {governanceSummary ? (
          <div className="space-y-2">
            <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded border border-border px-2 py-1">
                Total shared:{" "}
                <span data-testid="governance-total-count" className="font-semibold text-foreground">
                  {governanceSummary.total_shared_items}
                </span>
              </div>
              <div className="rounded border border-border px-2 py-1">
                Pending approvals:{" "}
                <span
                  data-testid="governance-pending-count"
                  className="font-semibold text-foreground"
                >
                  {governanceSummary.pending_approval_count}
                </span>
              </div>
              <div className="rounded border border-border px-2 py-1">
                Expiring in 7 days:{" "}
                <span
                  data-testid="governance-expiring-count"
                  className="font-semibold text-foreground"
                >
                  {governanceSummary.expiring_7d_count}
                </span>
              </div>
              <div className="rounded border border-border px-2 py-1">
                Expired:{" "}
                <span
                  data-testid="governance-expired-count"
                  className="font-semibold text-foreground"
                >
                  {governanceSummary.expired_count}
                </span>
              </div>
              <div className="rounded border border-border px-2 py-1">
                Scoped shares:{" "}
                <span
                  data-testid="governance-scoped-count"
                  className="font-semibold text-foreground"
                >
                  {governanceSummary.scoped_share_count}
                </span>
              </div>
              <div className="rounded border border-border px-2 py-1">
                Approved shares:{" "}
                <span className="font-semibold text-foreground">
                  {governanceSummary.approved_count}
                </span>
              </div>
            </div>

            <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
              <div className="rounded border border-border px-2 py-1">
                SLA approvals ({governanceTrends?.sla_hours ?? 24}h):{" "}
                <span
                  data-testid="governance-sla-percent"
                  className="font-semibold text-foreground"
                >
                  {governanceTrends ? `${governanceTrends.sla_approval_rate}%` : "N/A"}
                </span>
              </div>
              <div className="rounded border border-border px-2 py-1">
                Pending past SLA:{" "}
                <span
                  data-testid="governance-overdue-pending-count"
                  className="font-semibold text-foreground"
                >
                  {governanceTrends?.overdue_pending_count ?? "N/A"}
                </span>
              </div>
            </div>

            {latestTrendPoints.length > 0 && (
              <div className="rounded border border-border p-2">
                <p className="mb-1 text-xs font-medium text-foreground">
                  Last 7 days trend (new / approvals / SLA-within)
                </p>
                <div className="space-y-1 text-[11px] text-muted-foreground">
                  {latestTrendPoints.map((point) => (
                    <div
                      key={point.date}
                      className="flex items-center justify-between rounded border border-border/60 px-2 py-1"
                    >
                      <span>{point.date}</span>
                      <span>
                        {point.shared_count} / {point.approvals_completed_count} /{" "}
                        {point.approved_within_sla_count}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            Governance metrics unavailable for this workspace.
          </p>
        )}
      </div>

      <div className="rounded-lg border border-border bg-card p-3">
        <p className="mb-2 text-sm font-medium text-foreground">Governance Anomaly Alerts</p>
        <div className="space-y-2">
          {governanceAnomalies.length === 0 ? (
            <p className="text-xs text-muted-foreground">No anomaly alerts available.</p>
          ) : (
            governanceAnomalies.map((anomaly) => (
              <div
                key={anomaly.code}
                className="rounded border border-border px-2 py-1.5 text-xs"
                data-testid={`governance-anomaly-${anomaly.code}`}
              >
                <p
                  className={`font-medium ${
                    anomaly.severity === "critical"
                      ? "text-destructive"
                      : anomaly.severity === "warning"
                        ? "text-yellow-600"
                        : "text-foreground"
                  }`}
                >
                  {anomaly.title}
                </p>
                <p className="text-muted-foreground">{anomaly.description}</p>
                <p className="text-muted-foreground">
                  Recommendation: {anomaly.recommendation}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}
