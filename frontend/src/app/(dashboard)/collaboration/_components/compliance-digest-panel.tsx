"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import type {
  ComplianceDigestDeliveryList,
  ComplianceDigestPreview,
  ComplianceDigestSchedule,
  ShareGovernanceTrends,
} from "@/types";

interface ComplianceDigestPanelProps {
  digestSchedule: ComplianceDigestSchedule | null;
  digestPreview: ComplianceDigestPreview | null;
  digestDeliveries: ComplianceDigestDeliveryList | null;
  governanceTrends: ShareGovernanceTrends | null;
  isSavingDigest: boolean;
  isSendingDigest: boolean;
  onDigestScheduleChange: (schedule: ComplianceDigestSchedule | null) => void;
  onDigestPreviewChange: (preview: ComplianceDigestPreview | null) => void;
  onDigestDeliveriesChange: (deliveries: ComplianceDigestDeliveryList | null) => void;
  onSavingDigestChange: (saving: boolean) => void;
  onSendingDigestChange: (sending: boolean) => void;
  workspaceId: number;
}

export function ComplianceDigestPanel({
  digestSchedule,
  digestPreview,
  digestDeliveries,
  governanceTrends,
  isSavingDigest,
  isSendingDigest,
  onDigestScheduleChange,
  onDigestPreviewChange,
  onDigestDeliveriesChange,
  onSavingDigestChange,
  onSendingDigestChange,
  workspaceId,
}: ComplianceDigestPanelProps) {
  // Lazy-import the API to avoid circular deps — matches parent usage
  const apiRef = React.useRef<typeof import("@/lib/api").collaborationApi | null>(null);
  const getApi = React.useCallback(async () => {
    if (!apiRef.current) {
      const mod = await import("@/lib/api");
      apiRef.current = mod.collaborationApi;
    }
    return apiRef.current;
  }, []);
  const deliverySummary = digestPreview?.delivery_summary ?? digestDeliveries?.summary ?? null;
  const recentDeliveries = digestDeliveries?.items.slice(0, 5) ?? [];

  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-foreground">Compliance Digest</p>
        <Button
          size="sm"
          variant="outline"
          disabled={isSendingDigest || !digestSchedule?.is_enabled}
          onClick={async () => {
            onSendingDigestChange(true);
            try {
              const api = await getApi();
                  const preview = await api.sendComplianceDigest(workspaceId, {
                    days: governanceTrends?.days ?? 30,
                    sla_hours: governanceTrends?.sla_hours ?? 24,
                  });
                  onDigestPreviewChange(preview);
                  onDigestScheduleChange(preview.schedule);
                  const deliveries = await api
                    .getComplianceDigestDeliveries(workspaceId, { limit: 10 })
                    .catch(() => null);
                  onDigestDeliveriesChange(deliveries);
                } catch {
                  /* handled */
                } finally {
                  onSendingDigestChange(false);
            }
          }}
        >
          Send Now
        </Button>
      </div>
      {digestSchedule ? (
        <div className="space-y-2 text-xs">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            <label className="space-y-1 text-muted-foreground">
              Frequency
              <select
                className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                aria-label="Digest frequency"
                value={digestSchedule.frequency}
                onChange={(event) =>
                  onDigestScheduleChange({
                    ...digestSchedule,
                    frequency: event.target.value as "daily" | "weekly",
                  })
                }
              >
                <option value="daily">daily</option>
                <option value="weekly">weekly</option>
              </select>
            </label>
            <label className="space-y-1 text-muted-foreground">
              Day (weekly)
              <input
                aria-label="Digest day"
                type="number"
                min={0}
                max={6}
                className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                value={digestSchedule.day_of_week ?? 1}
                onChange={(event) =>
                  onDigestScheduleChange({
                    ...digestSchedule,
                    day_of_week: Number.parseInt(event.target.value, 10) || 0,
                  })
                }
              />
            </label>
            <label className="space-y-1 text-muted-foreground">
              Hour UTC
              <input
                aria-label="Digest hour UTC"
                type="number"
                min={0}
                max={23}
                className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                value={digestSchedule.hour_utc}
                onChange={(event) =>
                  onDigestScheduleChange({
                    ...digestSchedule,
                    hour_utc: Number.parseInt(event.target.value, 10) || 0,
                  })
                }
              />
            </label>
            <label className="space-y-1 text-muted-foreground">
              Minute UTC
              <input
                aria-label="Digest minute UTC"
                type="number"
                min={0}
                max={59}
                className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                value={digestSchedule.minute_utc}
                onChange={(event) =>
                  onDigestScheduleChange({
                    ...digestSchedule,
                    minute_utc: Number.parseInt(event.target.value, 10) || 0,
                  })
                }
              />
            </label>
            <label className="space-y-1 text-muted-foreground">
              Recipients
              <select
                className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                aria-label="Digest recipients"
                value={digestSchedule.recipient_role ?? "all"}
                onChange={(event) =>
                  onDigestScheduleChange({
                    ...digestSchedule,
                    recipient_role: event.target.value as
                      | "all"
                      | "owner"
                      | "admin"
                      | "contributor"
                      | "viewer",
                  })
                }
              >
                <option value="all">all workspace users</option>
                <option value="owner">owner only</option>
                <option value="admin">admins + owner</option>
                <option value="contributor">contributors</option>
                <option value="viewer">viewers</option>
              </select>
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-muted-foreground">
              <input
                type="checkbox"
                aria-label="Digest anomalies only"
                checked={digestSchedule.anomalies_only}
                onChange={(event) =>
                  onDigestScheduleChange({
                    ...digestSchedule,
                    anomalies_only: event.target.checked,
                  })
                }
              />
              anomalies only
            </label>
            <label className="flex items-center gap-2 text-muted-foreground">
              <input
                type="checkbox"
                aria-label="Digest enabled"
                checked={digestSchedule.is_enabled}
                onChange={(event) =>
                  onDigestScheduleChange({
                    ...digestSchedule,
                    is_enabled: event.target.checked,
                  })
                }
              />
              enabled
            </label>
            <Button
              size="sm"
              variant="outline"
              disabled={isSavingDigest}
              onClick={async () => {
                if (!digestSchedule) return;
                onSavingDigestChange(true);
                try {
                  const api = await getApi();
                  const updated = await api.updateComplianceDigestSchedule(
                    workspaceId,
                    {
                      frequency: digestSchedule.frequency,
                      day_of_week: digestSchedule.day_of_week,
                      hour_utc: digestSchedule.hour_utc,
                      minute_utc: digestSchedule.minute_utc,
                      channel: digestSchedule.channel,
                      recipient_role: digestSchedule.recipient_role,
                      anomalies_only: digestSchedule.anomalies_only,
                      is_enabled: digestSchedule.is_enabled,
                    }
                  );
                  onDigestScheduleChange(updated);
                  const preview = await api.getComplianceDigestPreview(workspaceId);
                  onDigestPreviewChange(preview);
                } catch {
                  /* handled */
                } finally {
                  onSavingDigestChange(false);
                }
              }}
            >
              Save Schedule
            </Button>
          </div>
          <p className="text-muted-foreground">
            Last sent:{" "}
            {digestSchedule.last_sent_at
              ? new Date(digestSchedule.last_sent_at).toLocaleString()
              : "never"}
          </p>
          {digestPreview ? (
            <p className="text-muted-foreground" data-testid="compliance-digest-preview">
              Preview anomalies: {digestPreview.anomalies.length} · pending approvals:{" "}
              {digestPreview.summary.pending_approval_count} · recipients:{" "}
              {digestPreview.recipient_count} ({digestPreview.recipient_role})
            </p>
          ) : (
            <p className="text-muted-foreground">
              Preview unavailable for this workspace.
            </p>
          )}
          {deliverySummary ? (
            <p
              className="text-muted-foreground"
              data-testid="compliance-digest-delivery-summary"
            >
              Delivery attempts: {deliverySummary.total_attempts} · success:{" "}
              {deliverySummary.success_count} · failed: {deliverySummary.failed_count} ·
              retry attempts: {deliverySummary.retry_attempt_count} · last status:{" "}
              {deliverySummary.last_status ?? "none"}
            </p>
          ) : (
            <p className="text-muted-foreground">
              Delivery telemetry unavailable for this workspace.
            </p>
          )}
          {recentDeliveries.length > 0 ? (
            <div className="space-y-1" data-testid="compliance-digest-delivery-list">
              {recentDeliveries.map((delivery) => (
                <div
                  key={delivery.id}
                  className="flex flex-wrap items-center gap-2 text-muted-foreground"
                  data-testid={`digest-delivery-row-${delivery.id}`}
                >
                  <span className="font-medium">{delivery.status}</span>
                  <span>attempt {delivery.attempt_number}</span>
                  <span>{delivery.recipient_count} recipients</span>
                  <span>{delivery.anomalies_count} anomalies</span>
                  {delivery.retry_of_delivery_id ? (
                    <span>retry of #{delivery.retry_of_delivery_id}</span>
                  ) : null}
                  {delivery.failure_reason ? <span>{delivery.failure_reason}</span> : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          Digest schedule unavailable for this workspace.
        </p>
      )}
    </div>
  );
}
