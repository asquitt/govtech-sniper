"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import type { TeamingDigestPreview, TeamingDigestSchedule } from "@/types";

interface DigestScheduleSectionProps {
  digestSchedule: TeamingDigestSchedule | null;
  digestPreview: TeamingDigestPreview | null;
  isSendingDigest: boolean;
  isSavingDigestSchedule: boolean;
  onSendDigest: () => void;
  onSaveSchedule: () => void;
  onScheduleChange: (schedule: TeamingDigestSchedule | null) => void;
}

export function DigestScheduleSection({
  digestSchedule,
  digestPreview,
  isSendingDigest,
  isSavingDigestSchedule,
  onSendDigest,
  onSaveSchedule,
  onScheduleChange,
}: DigestScheduleSectionProps) {
  return (
    <div className="rounded border border-border p-2 text-[11px] text-muted-foreground space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium text-foreground">Teaming Performance Digest</p>
        <Button
          size="sm"
          variant="outline"
          disabled={isSendingDigest || !digestSchedule?.is_enabled}
          onClick={onSendDigest}
        >
          Send Digest
        </Button>
      </div>
      {digestSchedule ? (
        <>
          <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
            <label className="space-y-1">
              Frequency
              <select
                className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                aria-label="Teaming digest frequency"
                value={digestSchedule.frequency}
                onChange={(event) =>
                  onScheduleChange({
                    ...digestSchedule,
                    frequency: event.target.value as "daily" | "weekly",
                  })
                }
              >
                <option value="daily">daily</option>
                <option value="weekly">weekly</option>
              </select>
            </label>
            <label className="space-y-1">
              Day
              <input
                aria-label="Teaming digest day"
                type="number"
                min={0}
                max={6}
                className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                value={digestSchedule.day_of_week ?? 1}
                onChange={(event) =>
                  onScheduleChange({
                    ...digestSchedule,
                    day_of_week: Number.parseInt(event.target.value, 10) || 0,
                  })
                }
              />
            </label>
            <label className="space-y-1">
              Hour UTC
              <input
                aria-label="Teaming digest hour"
                type="number"
                min={0}
                max={23}
                className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                value={digestSchedule.hour_utc}
                onChange={(event) =>
                  onScheduleChange({
                    ...digestSchedule,
                    hour_utc: Number.parseInt(event.target.value, 10) || 0,
                  })
                }
              />
            </label>
            <label className="space-y-1">
              Minute UTC
              <input
                aria-label="Teaming digest minute"
                type="number"
                min={0}
                max={59}
                className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                value={digestSchedule.minute_utc}
                onChange={(event) =>
                  onScheduleChange({
                    ...digestSchedule,
                    minute_utc: Number.parseInt(event.target.value, 10) || 0,
                  })
                }
              />
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                aria-label="Teaming digest include declined"
                checked={digestSchedule.include_declined_reasons}
                onChange={(event) =>
                  onScheduleChange({
                    ...digestSchedule,
                    include_declined_reasons: event.target.checked,
                  })
                }
              />
              include declined metrics
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                aria-label="Teaming digest enabled"
                checked={digestSchedule.is_enabled}
                onChange={(event) =>
                  onScheduleChange({
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
              disabled={isSavingDigestSchedule}
              onClick={onSaveSchedule}
            >
              Save Schedule
            </Button>
          </div>
          <p>
            Last sent:{" "}
            {digestSchedule.last_sent_at
              ? new Date(digestSchedule.last_sent_at).toLocaleString()
              : "never"}
          </p>
          {digestPreview ? (
            <p data-testid="teaming-digest-preview">
              Preview top partners: {digestPreview.top_partners.length}
            </p>
          ) : null}
        </>
      ) : (
        <p>Digest schedule unavailable.</p>
      )}
    </div>
  );
}
