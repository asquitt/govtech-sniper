"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { contractApi } from "@/lib/api";
import type { ContractStatusReport } from "@/types";

interface StatusReportsPanelProps {
  selectedContractId: number | null;
  statusReports: ContractStatusReport[];
  onStatusReportsChange: (reports: ContractStatusReport[]) => void;
  onError: (msg: string) => void;
}

export function StatusReportsPanel({
  selectedContractId,
  statusReports,
  onStatusReportsChange,
  onError,
}: StatusReportsPanelProps) {
  const [reportSummary, setReportSummary] = useState("");
  const [reportRisks, setReportRisks] = useState("");
  const [reportNextSteps, setReportNextSteps] = useState("");
  const [reportStart, setReportStart] = useState("");
  const [reportEnd, setReportEnd] = useState("");

  const handleCreateStatusReport = async () => {
    if (!selectedContractId) return;
    try {
      await contractApi.createStatusReport(selectedContractId, {
        period_start: reportStart || undefined,
        period_end: reportEnd || undefined,
        summary: reportSummary.trim() || undefined,
        risks: reportRisks.trim() || undefined,
        next_steps: reportNextSteps.trim() || undefined,
      });
      setReportSummary("");
      setReportRisks("");
      setReportNextSteps("");
      setReportStart("");
      setReportEnd("");
      const list = await contractApi.listStatusReports(selectedContractId);
      onStatusReportsChange(list);
    } catch (err) {
      console.error("Failed to create status report", err);
      onError("Failed to create status report.");
    }
  };

  return (
    <div className="mt-6 space-y-3">
      <p className="text-sm font-medium">Status Reports</p>
      <div className="grid grid-cols-2 gap-2">
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Period start (YYYY-MM-DD)"
          value={reportStart}
          onChange={(e) => setReportStart(e.target.value)}
        />
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Period end (YYYY-MM-DD)"
          value={reportEnd}
          onChange={(e) => setReportEnd(e.target.value)}
        />
        <input
          className="col-span-2 rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Summary"
          value={reportSummary}
          onChange={(e) => setReportSummary(e.target.value)}
        />
        <input
          className="col-span-2 rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Risks"
          value={reportRisks}
          onChange={(e) => setReportRisks(e.target.value)}
        />
        <input
          className="col-span-2 rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Next steps"
          value={reportNextSteps}
          onChange={(e) => setReportNextSteps(e.target.value)}
        />
      </div>
      <Button onClick={handleCreateStatusReport}>Add Status Report</Button>
      <div className="space-y-2">
        {statusReports.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No status reports yet.
          </p>
        ) : (
          statusReports.map((report) => (
            <div
              key={report.id}
              className="rounded-md border border-border px-3 py-2 text-sm space-y-1"
            >
              <div className="flex items-center justify-between">
                <span>
                  {report.period_start || "Period"} - {report.period_end || "End"}
                </span>
                <Badge variant="outline">
                  {report.created_at.slice(0, 10)}
                </Badge>
              </div>
              {report.summary && (
                <p className="text-xs text-muted-foreground">
                  {report.summary}
                </p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
