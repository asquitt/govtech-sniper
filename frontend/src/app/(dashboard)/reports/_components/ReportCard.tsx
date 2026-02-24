"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Clock, Download, Play, Send, Trash2 } from "lucide-react";
import type { ReportDataResponse, ReportType, SavedReport, ScheduleFrequency } from "@/types/report";

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

interface ReportCardProps {
  report: SavedReport;
  generatedData: ReportDataResponse | undefined;
  shareEmailValue: string;
  deliveryEmailValue: string;
  deliverySubjectValue: string;
  onShareEmailChange: (value: string) => void;
  onDeliveryEmailChange: (value: string) => void;
  onDeliverySubjectChange: (value: string) => void;
  onGenerate: (id: number) => void;
  onExport: (report: SavedReport) => void;
  onDelete: (id: number) => void;
  onSchedule: (id: number, frequency: ScheduleFrequency) => void;
  onSaveSharing: (report: SavedReport) => void;
  onSaveDelivery: (report: SavedReport) => void;
  onSendNow: (report: SavedReport) => void;
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

export function ReportCard({
  report,
  generatedData,
  shareEmailValue,
  deliveryEmailValue,
  deliverySubjectValue,
  onShareEmailChange,
  onDeliveryEmailChange,
  onDeliverySubjectChange,
  onGenerate,
  onExport,
  onDelete,
  onSchedule,
  onSaveSharing,
  onSaveDelivery,
  onSendNow,
}: ReportCardProps) {
  return (
    <Card>
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
                onSchedule(report.id, value as ScheduleFrequency);
              }}
            >
              <option value="">Schedule...</option>
              {SCHEDULE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <Button variant="ghost" size="sm" onClick={() => onGenerate(report.id)} title="Generate">
              <Play className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onExport(report)}
              title="Export CSV"
            >
              <Download className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(report.id)}
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
              value={shareEmailValue}
              onChange={(event) => onShareEmailChange(event.target.value)}
              placeholder="user1@agency.com, user2@agency.com"
              className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
            />
            <Button size="sm" variant="outline" onClick={() => onSaveSharing(report)}>
              Save Shared View
            </Button>
          </div>
          <div className="space-y-2 rounded-md border border-border p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Scheduled Email Delivery
            </p>
            <input
              type="text"
              value={deliveryEmailValue}
              onChange={(event) => onDeliveryEmailChange(event.target.value)}
              placeholder="exec@agency.com, ops@agency.com"
              className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
            />
            <input
              type="text"
              value={deliverySubjectValue}
              onChange={(event) => onDeliverySubjectChange(event.target.value)}
              placeholder="Delivery subject"
              className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
            />
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => onSaveDelivery(report)}>
                Save Delivery
              </Button>
              <Button size="sm" variant="outline" onClick={() => onSendNow(report)}>
                <Send className="mr-1 h-3.5 w-3.5" />
                Send Now
              </Button>
            </div>
          </div>
        </div>

        {generatedData && <ReportDataTable data={generatedData} />}
      </CardContent>
    </Card>
  );
}
