"use client";

import React from "react";
import { CheckCircle2, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { RFP, ComplianceRequirement } from "@/types";

interface StatusBarProps {
  rfp: RFP;
  requirements: ComplianceRequirement[];
}

export function StatusBar({ rfp, requirements }: StatusBarProps) {
  const addressed = requirements.filter((r) => r.is_addressed).length;
  const total = requirements.length;
  const completionPercent = total > 0 ? (addressed / total) * 100 : 0;

  return (
    <div className="flex items-center justify-between px-6 py-3 border-b border-border bg-card/30">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          {rfp.is_qualified ? (
            <CheckCircle2 className="w-5 h-5 text-accent" />
          ) : (
            <AlertCircle className="w-5 h-5 text-warning" />
          )}
          <span className="text-sm font-medium">
            {rfp.is_qualified
              ? `Qualified (${rfp.qualification_score}% match)`
              : "Pending Qualification"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {rfp.set_aside && <Badge variant="outline">{rfp.set_aside}</Badge>}
          {rfp.naics_code && <Badge variant="outline">NAICS {rfp.naics_code}</Badge>}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-xs text-muted-foreground">Proposal Completion</p>
          <p className="text-sm font-medium">
            {addressed}/{total} requirements
          </p>
        </div>
        <div className="w-32">
          <Progress value={completionPercent} />
        </div>
      </div>
    </div>
  );
}
