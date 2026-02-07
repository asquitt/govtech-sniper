"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Eraser,
  Loader2,
  Search,
  Shield,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  wordAddinSyncApi,
  type ComplianceCheckResult,
  type ComplianceIssueItem,
} from "@/lib/api/word-addin-client";
import {
  highlightText,
  clearHighlights,
  OfficeNotAvailableError,
} from "@/lib/office/word-document";
import type { ProposalSection } from "@/types";

interface ComplianceCheckPanelProps {
  section: ProposalSection | null;
  isInOffice: boolean;
}

const SEVERITY_CONFIG: Record<
  string,
  { icon: React.ElementType; color: string; bgColor: string; highlightColor: string }
> = {
  critical: {
    icon: XCircle,
    color: "text-red-500",
    bgColor: "bg-red-500/10 border-red-500/30",
    highlightColor: "Red",
  },
  warning: {
    icon: AlertTriangle,
    color: "text-yellow-500",
    bgColor: "bg-yellow-500/10 border-yellow-500/30",
    highlightColor: "Yellow",
  },
  info: {
    icon: Search,
    color: "text-blue-500",
    bgColor: "bg-blue-500/10 border-blue-500/30",
    highlightColor: "Turquoise",
  },
};

export function ComplianceCheckPanel({
  section,
  isInOffice,
}: ComplianceCheckPanelProps) {
  const [isChecking, setIsChecking] = useState(false);
  const [result, setResult] = useState<ComplianceCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!section) {
    return (
      <p className="text-xs text-muted-foreground py-4 text-center">
        Select a section from the Sections tab to check compliance.
      </p>
    );
  }

  const handleCheck = async () => {
    setIsChecking(true);
    setError(null);
    setResult(null);
    try {
      const data = await wordAddinSyncApi.checkCompliance(section.id);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compliance check failed");
    } finally {
      setIsChecking(false);
    }
  };

  const handleHighlightIssue = async (issue: ComplianceIssueItem) => {
    if (!isInOffice) return;
    try {
      // Try to highlight the first few words of the issue description in the document
      const searchSnippet = issue.issue.slice(0, 50);
      await highlightText(
        searchSnippet,
        SEVERITY_CONFIG[issue.severity]?.highlightColor || "Yellow"
      );
    } catch (err) {
      if (!(err instanceof OfficeNotAvailableError)) {
        console.error("Highlight failed:", err);
      }
    }
  };

  const handleClearHighlights = async () => {
    try {
      await clearHighlights();
    } catch (err) {
      if (!(err instanceof OfficeNotAvailableError)) {
        console.error("Clear highlights failed:", err);
      }
    }
  };

  const scoreColor =
    result && result.score >= 80
      ? "text-green-500"
      : result && result.score >= 60
        ? "text-yellow-500"
        : "text-red-500";

  return (
    <div className="space-y-3">
      {/* Section info */}
      <div className="rounded-md border border-border bg-card/50 p-2">
        <p className="text-xs font-medium truncate">
          {section.section_number}: {section.title}
        </p>
      </div>

      {/* Check button */}
      <Button
        size="sm"
        className="w-full text-xs"
        onClick={handleCheck}
        disabled={isChecking}
      >
        {isChecking ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : (
          <Shield className="w-3 h-3" />
        )}
        Run Compliance Check
      </Button>

      {error && (
        <p className="text-[11px] text-red-500 bg-red-500/10 border border-red-500/30 rounded-md px-2 py-1.5">
          {error}
        </p>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-2">
          {/* Summary */}
          <div className="flex items-center justify-between rounded-md border border-border p-2">
            <div className="flex items-center gap-1.5">
              {result.compliant ? (
                <CheckCircle2 className="w-4 h-4 text-green-500" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-yellow-500" />
              )}
              <span className="text-xs font-medium">
                {result.compliant ? "Compliant" : `${result.issues.length} issue${result.issues.length !== 1 ? "s" : ""}`}
              </span>
            </div>
            <span className={`text-sm font-bold ${scoreColor}`}>
              {Math.round(result.score)}
            </span>
          </div>

          {/* Clear highlights button */}
          {isInOffice && result.issues.length > 0 && (
            <Button
              size="sm"
              variant="outline"
              className="w-full text-xs"
              onClick={handleClearHighlights}
            >
              <Eraser className="w-3 h-3" />
              Clear Highlights
            </Button>
          )}

          {/* Issues list */}
          {result.issues.map((issue, i) => {
            const config = SEVERITY_CONFIG[issue.severity] || SEVERITY_CONFIG.info;
            const Icon = config.icon;

            return (
              <button
                key={i}
                className={`w-full text-left rounded-md border p-2 space-y-1 transition-colors hover:bg-accent/30 ${config.bgColor}`}
                onClick={() => handleHighlightIssue(issue)}
                disabled={!isInOffice}
              >
                <div className="flex items-start gap-1.5">
                  <Icon className={`w-3 h-3 shrink-0 mt-0.5 ${config.color}`} />
                  <span className="text-[11px]">{issue.issue}</span>
                </div>
                {issue.suggestion && (
                  <p className="text-[10px] text-muted-foreground ml-4">
                    Fix: {issue.suggestion}
                  </p>
                )}
                {issue.far_reference && (
                  <p className="text-[9px] text-muted-foreground ml-4 font-mono">
                    {issue.far_reference}
                  </p>
                )}
              </button>
            );
          })}

          {/* Suggestions */}
          {result.suggestions.length > 0 && (
            <div className="space-y-1">
              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">
                Suggestions
              </p>
              {result.suggestions.map((s, i) => (
                <p key={i} className="text-[11px] text-muted-foreground">
                  • {s}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
