"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { analyticsApi } from "@/lib/api";

const REPORT_OPTIONS = [
  { value: "win-rate", label: "Win Rate Trend" },
  { value: "pipeline", label: "Pipeline by Stage" },
  { value: "conversion", label: "Conversion Rates" },
  { value: "turnaround", label: "Proposal Turnaround" },
  { value: "naics", label: "NAICS Performance" },
] as const;

export function ExportButton() {
  const [exporting, setExporting] = useState(false);
  const [selected, setSelected] = useState("win-rate");

  const handleExport = async () => {
    setExporting(true);
    try {
      const csv = await analyticsApi.exportReport(selected, "csv");
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${selected}_export.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <select
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        className="h-9 rounded-md border border-border bg-background px-3 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
      >
        {REPORT_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <Button
        size="sm"
        variant="outline"
        onClick={handleExport}
        disabled={exporting}
      >
        <Download className="h-4 w-4 mr-1" />
        {exporting ? "Exporting..." : "Export CSV"}
      </Button>
    </div>
  );
}
