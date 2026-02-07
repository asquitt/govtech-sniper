"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { reportApi } from "@/lib/api/reports";
import type {
  SavedReport,
  SavedReportCreate,
  ReportType,
  ScheduleFrequency,
  ReportDataResponse,
} from "@/types/report";
import {
  FileBarChart,
  Plus,
  Download,
  Play,
  Clock,
  Trash2,
  X,
} from "lucide-react";

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

function NewReportForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (data: SavedReportCreate) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [reportType, setReportType] = useState<ReportType>("pipeline");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSubmit({ name: name.trim(), report_type: reportType });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">New Report</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              Report Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Monthly Pipeline Summary"
              className="w-full px-3 py-2 rounded-md border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              maxLength={255}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              Report Type
            </label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value as ReportType)}
              className="w-full px-3 py-2 rounded-md border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {REPORT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" disabled={!name.trim()}>
              <Plus className="w-4 h-4 mr-1" />
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
    <div className="overflow-x-auto rounded-md border border-border mt-3">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/30">
            {data.columns.map((col) => (
              <th
                key={col}
                className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase"
              >
                {col.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row, i) => (
            <tr key={i} className="border-b border-border last:border-0">
              {data.columns.map((col) => (
                <td key={col} className="px-3 py-2 text-foreground">
                  {String(row[col] ?? "-")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="px-3 py-1.5 text-xs text-muted-foreground bg-muted/20">
        {data.total_rows} row{data.total_rows !== 1 ? "s" : ""}
      </div>
    </div>
  );
}

export default function ReportsPage() {
  const [reports, setReports] = useState<SavedReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [generatedData, setGeneratedData] = useState<
    Record<number, ReportDataResponse>
  >({});

  const fetchReports = useCallback(async () => {
    try {
      const data = await reportApi.list();
      setReports(data);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleCreate = async (data: SavedReportCreate) => {
    try {
      await reportApi.create(data);
      setShowForm(false);
      fetchReports();
    } catch {
      // error handled
    }
  };

  const handleGenerate = async (id: number) => {
    try {
      const data = await reportApi.generate(id);
      setGeneratedData((prev) => ({ ...prev, [id]: data }));
      fetchReports();
    } catch {
      // error handled
    }
  };

  const handleExport = async (report: SavedReport) => {
    try {
      const blob = await reportApi.export(report.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${report.name.replace(/\s+/g, "_").toLowerCase()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // error handled
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await reportApi.delete(id);
      setReports((prev) => prev.filter((r) => r.id !== id));
      setGeneratedData((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    } catch {
      // error handled
    }
  };

  const handleSchedule = async (id: number, freq: ScheduleFrequency) => {
    try {
      await reportApi.setSchedule(id, freq);
      fetchReports();
    } catch {
      // error handled
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <Header
        title="Reports"
        description="Build, schedule, and export custom reports"
      />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Actions */}
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2 text-muted-foreground">
            <FileBarChart className="w-5 h-5" />
            <span className="text-sm">{reports.length} saved reports</span>
          </div>
          <Button onClick={() => setShowForm(!showForm)}>
            {showForm ? (
              <>
                <X className="w-4 h-4 mr-1" /> Cancel
              </>
            ) : (
              <>
                <Plus className="w-4 h-4 mr-1" /> New Report
              </>
            )}
          </Button>
        </div>

        {/* New Report Form */}
        {showForm && (
          <NewReportForm
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
          />
        )}

        {/* Report Cards */}
        {loading ? (
          <div className="text-center text-muted-foreground py-12">
            Loading reports...
          </div>
        ) : reports.length === 0 && !showForm ? (
          <Card>
            <CardContent className="py-12 text-center">
              <FileBarChart className="w-12 h-12 mx-auto text-muted-foreground mb-3" />
              <p className="text-muted-foreground">
                No reports yet. Create your first report to get started.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {reports.map((report) => (
              <Card key={report.id}>
                <CardContent className="py-4">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-foreground">
                          {report.name}
                        </h3>
                        <Badge
                          className={TYPE_COLORS[report.report_type]}
                          variant="secondary"
                        >
                          {report.report_type}
                        </Badge>
                        {report.schedule && (
                          <Badge variant="outline" className="text-xs">
                            <Clock className="w-3 h-3 mr-1" />
                            {report.schedule}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Last generated:{" "}
                        {report.last_generated_at
                          ? new Date(
                              report.last_generated_at
                            ).toLocaleDateString()
                          : "Never"}
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      <select
                        className="px-2 py-1 text-xs rounded border border-border bg-background text-foreground focus:outline-none"
                        value={report.schedule ?? ""}
                        onChange={(e) => {
                          if (e.target.value) {
                            handleSchedule(
                              report.id,
                              e.target.value as ScheduleFrequency
                            );
                          }
                        }}
                      >
                        <option value="">Schedule...</option>
                        {SCHEDULE_OPTIONS.map((s) => (
                          <option key={s.value} value={s.value}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleGenerate(report.id)}
                        title="Generate"
                      >
                        <Play className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleExport(report)}
                        title="Export CSV"
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(report.id)}
                        title="Delete"
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>

                  {/* Generated Data Table */}
                  {generatedData[report.id] && (
                    <ReportDataTable data={generatedData[report.id]} />
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
