"use client";

import { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { reportApi } from "@/lib/api/reports";
import type {
  ReportDataResponse,
  SavedReport,
  SavedReportCreate,
  ScheduleFrequency,
} from "@/types/report";
import { FileBarChart, Plus, X } from "lucide-react";
import { NewReportForm } from "./_components/NewReportForm";
import { ReportCard } from "./_components/ReportCard";

function parseEmails(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
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
              <ReportCard
                key={report.id}
                report={report}
                generatedData={generatedData[report.id]}
                shareEmailValue={shareEmailInputs[report.id] ?? ""}
                deliveryEmailValue={deliveryEmailInputs[report.id] ?? ""}
                deliverySubjectValue={deliverySubjects[report.id] ?? ""}
                onShareEmailChange={(value) =>
                  setShareEmailInputs((prev) => ({ ...prev, [report.id]: value }))
                }
                onDeliveryEmailChange={(value) =>
                  setDeliveryEmailInputs((prev) => ({ ...prev, [report.id]: value }))
                }
                onDeliverySubjectChange={(value) =>
                  setDeliverySubjects((prev) => ({ ...prev, [report.id]: value }))
                }
                onGenerate={handleGenerate}
                onExport={handleExport}
                onDelete={handleDelete}
                onSchedule={handleSchedule}
                onSaveSharing={handleSaveSharing}
                onSaveDelivery={handleSaveDelivery}
                onSendNow={handleSendNow}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
