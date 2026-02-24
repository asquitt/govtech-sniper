"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus } from "lucide-react";
import type { ReportType, SavedReportCreate, ScheduleFrequency } from "@/types/report";

const REPORT_TYPES: { value: ReportType; label: string }[] = [
  { value: "pipeline", label: "Pipeline" },
  { value: "proposals", label: "Proposals" },
  { value: "revenue", label: "Revenue" },
  { value: "activity", label: "Activity" },
];

const SCHEDULE_OPTIONS: { value: ScheduleFrequency; label: string }[] = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
];

const REPORT_FIELDS: Record<ReportType, string[]> = {
  pipeline: ["opportunity", "agency", "stage", "value", "due_date"],
  proposals: ["proposal", "rfp", "status", "score", "submitted_at"],
  revenue: ["contract", "agency", "monthly_revenue", "period"],
  activity: ["user", "action", "target", "timestamp"],
};

function parseEmails(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

interface NewReportFormProps {
  onSubmit: (data: SavedReportCreate) => void;
  onCancel: () => void;
}

export function NewReportForm({ onSubmit, onCancel }: NewReportFormProps) {
  const [name, setName] = useState("");
  const [reportType, setReportType] = useState<ReportType>("pipeline");
  const [selectedFields, setSelectedFields] = useState<string[]>(REPORT_FIELDS.pipeline.slice(0, 3));
  const [isShared, setIsShared] = useState(false);
  const [sharedWith, setSharedWith] = useState("");
  const [deliveryEnabled, setDeliveryEnabled] = useState(false);
  const [deliveryRecipients, setDeliveryRecipients] = useState("");
  const [deliverySubject, setDeliverySubject] = useState("");
  const [scheduleFrequency, setScheduleFrequency] = useState<ScheduleFrequency>("weekly");
  const [draggingField, setDraggingField] = useState<string | null>(null);

  useEffect(() => {
    setSelectedFields((prev) => {
      const allowed = REPORT_FIELDS[reportType];
      const intersection = prev.filter((field) => allowed.includes(field));
      if (intersection.length > 0) {
        return intersection;
      }
      return allowed.slice(0, 3);
    });
  }, [reportType]);

  const availableFields = useMemo(() => {
    return REPORT_FIELDS[reportType].filter((field) => !selectedFields.includes(field));
  }, [reportType, selectedFields]);

  const handleDropToSelected = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (!draggingField || selectedFields.includes(draggingField)) return;
    setSelectedFields((prev) => [...prev, draggingField]);
    setDraggingField(null);
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    onSubmit({
      name: name.trim(),
      report_type: reportType,
      config: {
        columns: selectedFields,
        filters: {},
        group_by: null,
        sort_by: null,
        sort_order: "asc",
      },
      schedule: scheduleFrequency,
      is_shared: isShared,
      shared_with_emails: parseEmails(sharedWith),
      delivery_enabled: deliveryEnabled,
      delivery_recipients: parseEmails(deliveryRecipients),
      delivery_subject: deliverySubject.trim() || null,
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">New Report</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-muted-foreground">Report Name</label>
              <input
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Monthly Pipeline Summary"
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                maxLength={255}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-muted-foreground">Report Type</label>
              <select
                value={reportType}
                onChange={(event) => setReportType(event.target.value as ReportType)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              >
                {REPORT_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <p className="mb-2 text-sm font-medium text-muted-foreground">Available Fields (drag to selected)</p>
              <div className="rounded-md border border-dashed border-border p-3">
                <div className="flex flex-wrap gap-2">
                  {availableFields.map((field) => (
                    <button
                      key={field}
                      type="button"
                      draggable
                      onDragStart={() => setDraggingField(field)}
                      className="cursor-grab rounded-md border border-border bg-muted px-2 py-1 text-xs"
                    >
                      {field}
                    </button>
                  ))}
                  {availableFields.length === 0 && (
                    <p className="text-xs text-muted-foreground">All fields selected.</p>
                  )}
                </div>
              </div>
            </div>
            <div>
              <p className="mb-2 text-sm font-medium text-muted-foreground">Selected Fields</p>
              <div
                onDragOver={(event) => event.preventDefault()}
                onDrop={handleDropToSelected}
                className="min-h-20 rounded-md border border-border p-3"
              >
                <div className="flex flex-wrap gap-2">
                  {selectedFields.map((field) => (
                    <span
                      key={field}
                      className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-1 text-xs text-primary"
                    >
                      {field}
                      <button
                        type="button"
                        aria-label={`Remove ${field}`}
                        onClick={() =>
                          setSelectedFields((prev) => prev.filter((item) => item !== field))
                        }
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={isShared}
                  onChange={(event) => setIsShared(event.target.checked)}
                />
                Share saved report view
              </label>
              <input
                type="text"
                value={sharedWith}
                onChange={(event) => setSharedWith(event.target.value)}
                placeholder="teammate@agency.com, capture@agency.com"
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-2">
              <label className="mb-1 block text-sm font-medium text-muted-foreground">
                Delivery Frequency
              </label>
              <select
                value={scheduleFrequency}
                onChange={(event) => setScheduleFrequency(event.target.value as ScheduleFrequency)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              >
                {SCHEDULE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={deliveryEnabled}
                  onChange={(event) => setDeliveryEnabled(event.target.checked)}
                />
                Enable email delivery
              </label>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <input
              type="text"
              value={deliveryRecipients}
              onChange={(event) => setDeliveryRecipients(event.target.value)}
              placeholder="delivery@agency.com, executive@agency.com"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
            <input
              type="text"
              value={deliverySubject}
              onChange={(event) => setDeliverySubject(event.target.value)}
              placeholder="Weekly Pipeline Update"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" disabled={!name.trim()}>
              <Plus className="mr-1 h-4 w-4" />
              Create
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
