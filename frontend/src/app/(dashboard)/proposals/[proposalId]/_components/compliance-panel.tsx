"use client";

import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { analysisApi } from "@/lib/api";
import type { ComplianceMatrix, ComplianceRequirement } from "@/types";

interface CompliancePanelProps {
  rfpId: number;
  onSelectRequirement?: (requirementId: string) => void;
}

function ConfidenceBadge({ confidence }: { confidence: number | undefined }) {
  if (confidence == null) return null;
  if (confidence >= 0.8) {
    return <Badge variant="outline" className="text-[10px] border-green-500 text-green-700">High</Badge>;
  }
  if (confidence >= 0.5) {
    return <Badge variant="outline" className="text-[10px] border-yellow-500 text-yellow-700">Med</Badge>;
  }
  return <Badge variant="outline" className="text-[10px] border-red-500 text-red-700">Low</Badge>;
}

export function CompliancePanel({ rfpId, onSelectRequirement }: CompliancePanelProps) {
  const [matrix, setMatrix] = useState<ComplianceMatrix | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showGapsOnly, setShowGapsOnly] = useState(false);

  const loadMatrix = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await analysisApi.getComplianceMatrix(rfpId);
      setMatrix(data);
    } catch (err) {
      console.error("Failed to load compliance matrix", err);
    } finally {
      setIsLoading(false);
    }
  }, [rfpId]);

  useEffect(() => {
    loadMatrix();
  }, [loadMatrix]);

  if (isLoading) {
    return (
      <Card className="border border-border">
        <CardContent className="p-4 flex items-center justify-center">
          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (!matrix || matrix.requirements.length === 0) {
    return (
      <Card className="border border-border">
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground text-center">
            No compliance matrix available. Run Deep Read analysis first.
          </p>
        </CardContent>
      </Card>
    );
  }

  const requirements = matrix.requirements;
  const addressed = requirements.filter((r) => r.is_addressed).length;
  const mandatoryGaps = requirements.filter(
    (r) => r.importance === "mandatory" && !r.is_addressed
  ).length;

  const displayed = showGapsOnly
    ? requirements.filter((r) => !r.is_addressed)
    : requirements;

  // Sort: mandatory first, then by importance
  const sorted = [...displayed].sort((a, b) => {
    const order = { mandatory: 0, evaluated: 1, optional: 2, informational: 3 };
    return (order[a.importance] ?? 4) - (order[b.importance] ?? 4);
  });

  return (
    <Card className="border border-border">
      <CardHeader className="pb-2 px-4 pt-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-1.5">
            <Shield className="w-4 h-4" />
            Compliance
          </CardTitle>
          <Button
            variant={showGapsOnly ? "default" : "outline"}
            size="sm"
            className="h-6 text-[10px] px-2"
            onClick={() => setShowGapsOnly(!showGapsOnly)}
          >
            {showGapsOnly ? "Show All" : "Gaps Only"}
          </Button>
        </div>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-xs text-muted-foreground">
            {addressed}/{requirements.length} addressed
          </span>
          {mandatoryGaps > 0 && (
            <span className="text-xs text-red-600 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              {mandatoryGaps} mandatory gap{mandatoryGaps > 1 ? "s" : ""}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-3 max-h-[400px] overflow-y-auto">
        <div className="space-y-2">
          {sorted.map((req) => (
            <RequirementRow
              key={req.id}
              requirement={req}
              onClick={() => onSelectRequirement?.(req.id)}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function RequirementRow({
  requirement: req,
  onClick,
}: {
  requirement: ComplianceRequirement;
  onClick: () => void;
}) {
  return (
    <button
      className="w-full text-left p-2 rounded border border-border hover:bg-accent/50 transition-colors"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            {req.is_addressed ? (
              <CheckCircle2 className="w-3 h-3 text-green-600 shrink-0" />
            ) : (
              <AlertTriangle className="w-3 h-3 text-amber-500 shrink-0" />
            )}
            <span className="text-[11px] font-medium truncate">{req.section}</span>
          </div>
          <p className="text-[11px] text-muted-foreground line-clamp-2">
            {req.requirement_text}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <Badge
            variant="outline"
            className={`text-[9px] ${
              req.importance === "mandatory"
                ? "border-red-400 text-red-700"
                : req.importance === "evaluated"
                  ? "border-blue-400 text-blue-700"
                  : "border-gray-300 text-gray-600"
            }`}
          >
            {req.importance}
          </Badge>
          <ConfidenceBadge confidence={req.confidence} />
        </div>
      </div>
      {req.source_section && (
        <p className="text-[10px] text-muted-foreground mt-1">{req.source_section}</p>
      )}
    </button>
  );
}
