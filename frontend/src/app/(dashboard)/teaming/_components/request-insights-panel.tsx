"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { teamingBoardApi } from "@/lib/api";
import type {
  TeamingDigestPreview,
  TeamingDigestSchedule,
  TeamingPartnerTrendDrilldownResponse,
  TeamingRequestTrend,
} from "@/types";
import { DigestScheduleSection } from "./digest-schedule-section";

interface RequestInsightsPanelProps {
  direction: "sent" | "received" | "all";
  requestFitTrends: TeamingRequestTrend | null;
  partnerDrilldowns: TeamingPartnerTrendDrilldownResponse | null;
  digestSchedule: TeamingDigestSchedule | null;
  digestPreview: TeamingDigestPreview | null;
  onDigestScheduleChange: (schedule: TeamingDigestSchedule | null) => void;
  onDigestPreviewChange: (preview: TeamingDigestPreview | null) => void;
  onError: (message: string) => void;
}

export function RequestInsightsPanel({
  direction,
  requestFitTrends,
  partnerDrilldowns,
  digestSchedule,
  digestPreview,
  onDigestScheduleChange,
  onDigestPreviewChange,
  onError,
}: RequestInsightsPanelProps) {
  const [isExportingTimeline, setIsExportingTimeline] = useState(false);
  const [isSavingDigestSchedule, setIsSavingDigestSchedule] = useState(false);
  const [isSendingDigest, setIsSendingDigest] = useState(false);

  const recentTrendPoints = (requestFitTrends?.points ?? []).slice(-7).reverse();

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>Teaming Fit Trends</CardTitle>
        <Button
          size="sm"
          variant="outline"
          data-testid="teaming-export-audit"
          disabled={isExportingTimeline}
          onClick={async () => {
            setIsExportingTimeline(true);
            try {
              const blob = await teamingBoardApi.exportRequestAuditCsv(direction, 30);
              const url = window.URL.createObjectURL(blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = "teaming_requests_audit.csv";
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
              window.URL.revokeObjectURL(url);
            } catch {
              onError("Failed to export request audit timeline.");
            } finally {
              setIsExportingTimeline(false);
            }
          }}
        >
          Export Timeline CSV
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground lg:grid-cols-4">
          <div className="rounded border border-border px-2 py-1">
            Total sent:{" "}
            <span data-testid="teaming-total-sent" className="font-semibold text-foreground">
              {requestFitTrends?.total_sent ?? 0}
            </span>
          </div>
          <div className="rounded border border-border px-2 py-1">
            Accepted:{" "}
            <span data-testid="teaming-accepted-count" className="font-semibold text-foreground">
              {requestFitTrends?.accepted_count ?? 0}
            </span>
          </div>
          <div className="rounded border border-border px-2 py-1">
            Pending:{" "}
            <span data-testid="teaming-pending-count" className="font-semibold text-foreground">
              {requestFitTrends?.pending_count ?? 0}
            </span>
          </div>
          <div className="rounded border border-border px-2 py-1">
            Acceptance rate:{" "}
            <span data-testid="teaming-acceptance-rate" className="font-semibold text-foreground">
              {requestFitTrends ? `${requestFitTrends.acceptance_rate}%` : "0%"}
            </span>
          </div>
        </div>
        {recentTrendPoints.length > 0 && (
          <div className="rounded border border-border p-2 text-[11px] text-muted-foreground">
            <p className="mb-1 font-medium text-foreground">Last 7 days fit-score trend</p>
            <div className="space-y-1">
              {recentTrendPoints.map((point) => (
                <div
                  key={point.date}
                  className="flex items-center justify-between rounded border border-border/60 px-2 py-1"
                >
                  <span>{point.date}</span>
                  <span>
                    sent {point.sent_count} / accepted {point.accepted_count} / fit{" "}
                    {point.fit_score}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="rounded border border-border p-2 text-[11px] text-muted-foreground">
          <p className="mb-1 font-medium text-foreground">Partner Drilldowns</p>
          {partnerDrilldowns && partnerDrilldowns.partners.length > 0 ? (
            <div className="space-y-1">
              {partnerDrilldowns.partners.slice(0, 5).map((partner) => (
                <div
                  key={partner.partner_id}
                  className="flex items-center justify-between rounded border border-border/60 px-2 py-1"
                  data-testid={`partner-drilldown-${partner.partner_id}`}
                >
                  <span>{partner.partner_name}</span>
                  <span>
                    sent {partner.sent_count} / accepted {partner.accepted_count} / rate{" "}
                    {partner.acceptance_rate}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p>No partner drilldown data yet.</p>
          )}
        </div>
        <DigestScheduleSection
          digestSchedule={digestSchedule}
          digestPreview={digestPreview}
          isSendingDigest={isSendingDigest}
          isSavingDigestSchedule={isSavingDigestSchedule}
          onSendDigest={async () => {
            setIsSendingDigest(true);
            try {
              const preview = await teamingBoardApi.sendDigest(30);
              onDigestPreviewChange(preview);
              onDigestScheduleChange(preview.schedule);
            } catch {
              onError("Failed to send teaming digest.");
            } finally {
              setIsSendingDigest(false);
            }
          }}
          onSaveSchedule={async () => {
            if (!digestSchedule) return;
            setIsSavingDigestSchedule(true);
            try {
              const updated = await teamingBoardApi.updateDigestSchedule({
                frequency: digestSchedule.frequency,
                day_of_week: digestSchedule.day_of_week,
                hour_utc: digestSchedule.hour_utc,
                minute_utc: digestSchedule.minute_utc,
                channel: digestSchedule.channel,
                include_declined_reasons: digestSchedule.include_declined_reasons,
                is_enabled: digestSchedule.is_enabled,
              });
              onDigestScheduleChange(updated);
            } catch {
              onError("Failed to save digest schedule.");
            } finally {
              setIsSavingDigestSchedule(false);
            }
          }}
          onScheduleChange={onDigestScheduleChange}
        />
      </CardContent>
    </Card>
  );
}
