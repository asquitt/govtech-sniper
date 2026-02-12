"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { reportApi } from "@/lib/api/reports";
import type {
  ReportDataResponse,
  ReportType,
  SavedReport,
  SavedReportCreate,
  ScheduleFrequency,
} from "@/types/report";
import { Clock, Download, FileBarChart, Play, Plus, Send, Trash2, X } from "lucide-react";

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

const TYPE_COLORS: Record<ReportType, string> = {
  pipeline: "bg-blue-500/20 text-blue-400",
  proposals: "bg-purple-500/20 text-purple-400",
  revenue: "bg-green-500/20 text-green-400",
  activity: "bg-orange-500/20 text-orange-400",
};

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

function NewReportForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (data: SavedReportCreate) => void;
  onCancel: () => void;
}) {
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

function ReportDataTable({ data }: { data: ReportDataResponse }) {
  return (
    <div className="mt-3 overflow-x-auto rounded-md border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/30">
            {data.columns.map((column) => (
              <th key={column} className="px-3 py-2 text-left text-xs font-medium uppercase text-muted-foreground">
                {column.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row, index) => (
            <tr key={index} className="border-b border-border last:border-0">
              {data.columns.map((column) => (
                <td key={column} className="px-3 py-2 text-foreground">
                  {String(row[column] ?? "-")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="bg-muted/20 px-3 py-1.5 text-xs text-muted-foreground">
        {data.total_rows} row{data.total_rows === 1 ? "" : "s"}
      </div>
    </div>
  );
}

export default function ReportsPage() {
  const [reports, setReports] = useState<SavedReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedData, setGeneratedData] = useState<Record<number, ReportDataResponse>>({});
  const [shareEmailInputs, setShareEmailInputs] = useState<Record<number, string>>({});
  const [deliveryEmailInputs, setDeliveryEmailInputs] = useState<Record<number, string>>({});
  const [deliverySubjects, setDeliverySubjects] = useState<Record<number, string>>({});

  const fetchReports = useCallback(async () => {
    try {
      const data = await reportApi.list();
      setReports(data);
      setShareEmailInputs(
        Object.fromEntries(data.map((report) => [report.id, report.shared_with_emails.join(", ")]))
      );
      setDeliveryEmailInputs(
        Object.fromEntries(data.map((report) => [report.id, report.delivery_recipients.join(", ")]))
      );
      setDeliverySubjects(
        Object.fromEntries(data.map((report) => [report.id, report.delivery_subject ?? ""]))
      );
    } catch {
      setError("Failed to load reports.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleCreate = async (payload: SavedReportCreate) => {
    setError(null);
    try {
      await reportApi.create(payload);
      setShowForm(false);
      await fetchReports();
    } catch {
      setError("Failed to create report.");
    }
  };

  const handleGenerate = async (id: number) => {
    setError(null);
    try {
      const data = await reportApi.generate(id);
      setGeneratedData((prev) => ({ ...prev, [id]: data }));
      await fetchReports();
    } catch {
      setError("Failed to generate report.");
    }
  };

  const handleExport = async (report: SavedReport) => {
    setError(null);
    try {
      const blob = await reportApi.export(report.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${report.name.replace(/\s+/g, "_").toLowerCase()}.csv`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Failed to export report.");
    }
  };

  const handleDelete = async (id: number) => {
    setError(null);
    try {
      await reportApi.delete(id);
      setReports((prev) => prev.filter((report) => report.id !== id));
      setGeneratedData((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    } catch {
      setError("Failed to delete report.");
    }
  };

  const handleSchedule = async (id: number, frequency: ScheduleFrequency) => {
    setError(null);
    try {
      await reportApi.setSchedule(id, frequency);
      await fetchReports();
    } catch {
      setError("Failed to update schedule.");
    }
  };

  const handleSaveSharing = async (report: SavedReport) => {
    setError(null);
    try {
      const recipients = parseEmails(shareEmailInputs[report.id] ?? "");
      await reportApi.share(report.id, {
        is_shared: recipients.length > 0,
        shared_with_emails: recipients,
      });
      await fetchReports();
    } catch {
      setError("Failed to save report sharing.");
    }
  };

  const handleSaveDelivery = async (report: SavedReport) => {
    setError(null);
    try {
      const recipients = parseEmails(deliveryEmailInputs[report.id] ?? "");
      const frequency = report.schedule ?? "weekly";
      await reportApi.setSchedule(report.id, frequency, {
        frequency,
        recipients,
        enabled: recipients.length > 0,
        subject: (deliverySubjects[report.id] ?? "").trim() || undefined,
      });
      await fetchReports();
    } catch {
      setError("Failed to save report delivery settings.");
    }
  };

  const handleSendNow = async (report: SavedReport) => {
    setError(null);
    try {
      await reportApi.sendDeliveryNow(report.id);
      await fetchReports();
    } catch {
      setError("Delivery send failed. Ensure schedule and recipients are configured.");
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <Header title="Reports" description="Build, share, schedule, and export custom reports" />
      <div className="flex-1 space-y-6 overflow-y-auto p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-muted-foreground">
            <FileBarChart className="h-5 w-5" />
            <span className="text-sm">{reports.length} saved reports</span>
          </div>
          <Button onClick={() => setShowForm((prev) => !prev)}>
            {showForm ? (
              <>
                <X className="mr-1 h-4 w-4" /> Cancel
              </>
            ) : (
              <>
                <Plus className="mr-1 h-4 w-4" /> New Report
              </>
            )}
          </Button>
        </div>

        {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

        {showForm && <NewReportForm onSubmit={handleCreate} onCancel={() => setShowForm(false)} />}

        {loading ? (
          <div className="py-12 text-center text-muted-foreground">Loading reports...</div>
        ) : reports.length === 0 && !showForm ? (
          <Card>
            <CardContent className="py-12 text-center">
              <FileBarChart className="mx-auto mb-3 h-12 w-12 text-muted-foreground" />
              <p className="text-muted-foreground">No reports yet. Create your first report to get started.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {reports.map((report) => (
              <Card key={report.id}>
                <CardContent className="space-y-4 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-medium text-foreground">{report.name}</h3>
                        <Badge className={TYPE_COLORS[report.report_type]} variant="secondary">
                          {report.report_type}
                        </Badge>
                        {report.schedule && (
                          <Badge variant="outline" className="text-xs">
                            <Clock className="mr-1 h-3 w-3" />
                            {report.schedule}
                          </Badge>
                        )}
                        {report.is_shared && <Badge variant="secondary">Shared View</Badge>}
                        {report.delivery_enabled && <Badge variant="secondary">Email Delivery</Badge>}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Last generated:{" "}
                        {report.last_generated_at
                          ? new Date(report.last_generated_at).toLocaleDateString()
                          : "Never"}
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {(report.config.columns ?? []).map((column) => (
                          <Badge key={column} variant="outline" className="text-[10px]">
                            {column}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <select
                        className="rounded border border-border bg-background px-2 py-1 text-xs text-foreground focus:outline-none"
                        value={report.schedule ?? ""}
                        onChange={(event) => {
                          const value = event.target.value;
                          if (!value) return;
                          handleSchedule(report.id, value as ScheduleFrequency);
                        }}
                      >
                        <option value="">Schedule...</option>
                        {SCHEDULE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      <Button variant="ghost" size="sm" onClick={() => handleGenerate(report.id)} title="Generate">
                        <Play className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleExport(report)}
                        title="Export CSV"
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(report.id)}
                        title="Delete"
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    <div className="space-y-2 rounded-md border border-border p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Saved View Sharing
                      </p>
                      <input
                        type="text"
                        value={shareEmailInputs[report.id] ?? ""}
                        onChange={(event) =>
                          setShareEmailInputs((prev) => ({ ...prev, [report.id]: event.target.value }))
                        }
                        placeholder="user1@agency.com, user2@agency.com"
                        className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
                      />
                      <Button size="sm" variant="outline" onClick={() => handleSaveSharing(report)}>
                        Save Shared View
                      </Button>
                    </div>
                    <div className="space-y-2 rounded-md border border-border p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Scheduled Email Delivery
                      </p>
                      <input
                        type="text"
                        value={deliveryEmailInputs[report.id] ?? ""}
                        onChange={(event) =>
                          setDeliveryEmailInputs((prev) => ({
                            ...prev,
                            [report.id]: event.target.value,
                          }))
                        }
                        placeholder="exec@agency.com, ops@agency.com"
                        className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
                      />
                      <input
                        type="text"
                        value={deliverySubjects[report.id] ?? ""}
                        onChange={(event) =>
                          setDeliverySubjects((prev) => ({
                            ...prev,
                            [report.id]: event.target.value,
                          }))
                        }
                        placeholder="Delivery subject"
                        className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
                      />
                      <div className="flex items-center gap-2">
                        <Button size="sm" variant="outline" onClick={() => handleSaveDelivery(report)}>
                          Save Delivery
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleSendNow(report)}>
                          <Send className="mr-1 h-3.5 w-3.5" />
                          Send Now
                        </Button>
                      </div>
                    </div>
                  </div>

                  {generatedData[report.id] && <ReportDataTable data={generatedData[report.id]} />}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
