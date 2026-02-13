"use client";

import React from "react";
import { ArrowLeft, Download, List, Grid3X3, Plus, Loader2 } from "lucide-react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import type { RFP } from "@/types";

interface AnalysisHeaderProps {
  rfp: RFP;
  viewMode: "list" | "shred";
  onViewModeChange: (mode: "list" | "shred") => void;
  onAddRequirement: () => void;
  onExport: () => void;
  isExporting: boolean;
}

export function AnalysisHeader({
  rfp,
  viewMode,
  onViewModeChange,
  onAddRequirement,
  onExport,
  isExporting,
}: AnalysisHeaderProps) {
  return (
    <Header
      title={rfp.title}
      description={`${rfp.solicitation_number} • ${rfp.agency}`}
      actions={
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link href="/opportunities">
              <ArrowLeft className="w-4 h-4" />
              Back
            </Link>
          </Button>
          <div className="flex items-center border border-border rounded-lg">
            <Button
              variant={viewMode === "list" ? "default" : "ghost"}
              size="sm"
              onClick={() => onViewModeChange("list")}
              className="rounded-r-none"
            >
              <List className="w-4 h-4" />
            </Button>
            <Button
              variant={viewMode === "shred" ? "default" : "ghost"}
              size="sm"
              onClick={() => onViewModeChange("shred")}
              className="rounded-l-none"
            >
              <Grid3X3 className="w-4 h-4" />
            </Button>
          </div>
          <Button variant="outline" onClick={onAddRequirement}>
            <Plus className="w-4 h-4" />
            Add Requirement
          </Button>
          <Button
            variant="outline"
            onClick={onExport}
            disabled={isExporting}
          >
            {isExporting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            Export
          </Button>
        </div>
      }
    />
  );
}
