"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type {
  ComplianceTrustMetrics,
  TrustCenterPolicy,
  TrustCenterProfile,
} from "@/types/compliance";

function trustStatusClass(status: "enforced" | "warning" | "configured"): string {
  if (status === "enforced") {
    return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  }
  if (status === "warning") {
    return "bg-destructive/10 text-destructive";
  }
  return "bg-primary/10 text-primary";
}

interface TrustCenterCardProps {
  trustCenter: TrustCenterProfile | null;
  trustMetrics: ComplianceTrustMetrics | null;
  policyDraft: TrustCenterPolicy | null;
  policySaving: boolean;
  policyError: string | null;
  policySavedMessage: string | null;
  unsavedPolicyChanges: boolean;
  trustExportFormat: "json" | "csv" | "pdf";
  signedTrustExports: boolean;
  evidenceExporting: boolean;
  threePaoExporting: boolean;
  onTrustExportFormatChange: (format: "json" | "csv" | "pdf") => void;
  onSignedTrustExportsChange: (signed: boolean) => void;
  onTrustEvidenceExport: () => void;
  onThreePaoExport: () => void;
  onPolicySave: (event: React.FormEvent) => void;
  onUpdateDraftBoolean: (
    key:
      | "allow_ai_requirement_analysis"
      | "allow_ai_draft_generation"
      | "require_human_review_for_submission"
      | "share_anonymized_product_telemetry",
    value: boolean
  ) => void;
  onUpdateDraftNumber: (
    key: "retain_prompt_logs_days" | "retain_output_logs_days",
    value: number
  ) => void;
}

export function TrustCenterCard({
  trustCenter,
  trustMetrics,
  policyDraft,
  policySaving,
  policyError,
  policySavedMessage,
  unsavedPolicyChanges,
  trustExportFormat,
  signedTrustExports,
  evidenceExporting,
  threePaoExporting,
  onTrustExportFormatChange,
  onSignedTrustExportsChange,
  onTrustEvidenceExport,
  onThreePaoExport,
  onPolicySave,
  onUpdateDraftBoolean,
  onUpdateDraftNumber,
}: TrustCenterCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>AI & Data Trust Center</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Evidence completeness</p>
            <p className="text-sm font-medium">
              {trustMetrics?.checkpoint_evidence_completeness_rate ?? 0}%
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Sign-off completion</p>
            <p className="text-sm font-medium">
              {trustMetrics?.checkpoint_signoff_completion_rate ?? 0}%
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Trust export success (30d)</p>
            <p className="text-sm font-medium">
              {trustMetrics?.trust_export_success_rate_30d ?? 0}%
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Step-up success (30d)</p>
            <p className="text-sm font-medium">
              {trustMetrics?.step_up_challenge_success_rate_30d ?? 0}%
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Model provider</p>
            <p className="text-sm font-medium">
              {trustCenter?.runtime_guarantees.model_provider ?? "Google Gemini API"}
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Processing mode</p>
            <p className="text-sm font-medium">
              {trustCenter?.runtime_guarantees.processing_mode ?? "ephemeral_no_training"}
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Provider retention window</p>
            <p className="text-sm font-medium">
              {trustCenter?.runtime_guarantees.provider_retention_hours ?? 0} hour(s)
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant={
              trustCenter?.runtime_guarantees.no_training_enforced
                ? "default"
                : "destructive"
            }
          >
            {trustCenter?.runtime_guarantees.no_training_enforced
              ? "No model training enforced"
              : "Training protection requires remediation"}
          </Badge>
          <Badge variant="outline">
            Last updated {trustCenter ? new Date(trustCenter.updated_at).toLocaleString() : "n/a"}
          </Badge>
          {trustCenter?.organization_name ? (
            <Badge variant="outline">Org: {trustCenter.organization_name}</Badge>
          ) : (
            <Badge variant="outline">No organization policy scope</Badge>
          )}
          <select
            aria-label="Trust export format"
            className="h-8 rounded-md border border-input bg-background px-2 text-xs"
            value={trustExportFormat}
            onChange={(event) =>
              onTrustExportFormatChange(event.target.value as "json" | "csv" | "pdf")
            }
            disabled={evidenceExporting || threePaoExporting}
          >
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
            <option value="pdf">PDF</option>
          </select>
          <label className="inline-flex h-8 items-center gap-2 rounded-md border border-input px-2 text-xs">
            <input
              aria-label="Signed trust export toggle"
              type="checkbox"
              checked={signedTrustExports}
              onChange={(event) => onSignedTrustExportsChange(event.target.checked)}
              disabled={evidenceExporting || threePaoExporting}
            />
            Signed export
          </label>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={evidenceExporting}
            onClick={onTrustEvidenceExport}
          >
            {evidenceExporting ? "Exporting..." : "Export Trust Evidence"}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={threePaoExporting}
            onClick={onThreePaoExport}
          >
            {threePaoExporting
              ? "Exporting..."
              : "Export 3PAO Readiness Package"}
          </Button>
        </div>

        <div className="space-y-2">
          {trustCenter?.evidence.map((item) => (
            <div
              key={item.control}
              className="rounded-lg border border-border px-3 py-2 flex flex-wrap items-start justify-between gap-2"
            >
              <div className="space-y-1 min-w-0">
                <p className="text-sm font-medium">{item.control}</p>
                <p className="text-xs text-muted-foreground">{item.detail}</p>
              </div>
              <span
                className={`text-[10px] uppercase tracking-wide rounded px-2 py-1 ${trustStatusClass(item.status)}`}
              >
                {item.status}
              </span>
            </div>
          ))}
        </div>

        <div className="rounded-lg border border-border p-4 space-y-3">
          <p className="text-sm font-medium">Policy Controls</p>
          {!trustCenter?.can_manage_policy && (
            <p className="text-xs text-muted-foreground">
              Visibility is enabled for all users. Organization owners/admins can edit these controls.
            </p>
          )}
          <form className="space-y-3" onSubmit={onPolicySave}>
            <label className="flex items-start justify-between gap-3 rounded-md border border-border px-3 py-2">
              <div className="space-y-1">
                <p className="text-sm text-foreground">AI requirement analysis enabled</p>
                <p className="text-xs text-muted-foreground">
                  Controls use of AI for requirement extraction and compliance analysis.
                </p>
              </div>
              <input
                aria-label="AI requirement analysis toggle"
                type="checkbox"
                checked={policyDraft?.allow_ai_requirement_analysis ?? false}
                disabled={!trustCenter?.can_manage_policy || policySaving}
                onChange={(event) =>
                  onUpdateDraftBoolean("allow_ai_requirement_analysis", event.target.checked)
                }
              />
            </label>

            <label className="flex items-start justify-between gap-3 rounded-md border border-border px-3 py-2">
              <div className="space-y-1">
                <p className="text-sm text-foreground">AI draft generation enabled</p>
                <p className="text-xs text-muted-foreground">
                  Controls AI-generated proposal drafting and section rewrites.
                </p>
              </div>
              <input
                aria-label="AI draft generation toggle"
                type="checkbox"
                checked={policyDraft?.allow_ai_draft_generation ?? false}
                disabled={!trustCenter?.can_manage_policy || policySaving}
                onChange={(event) =>
                  onUpdateDraftBoolean("allow_ai_draft_generation", event.target.checked)
                }
              />
            </label>

            <label className="flex items-start justify-between gap-3 rounded-md border border-border px-3 py-2">
              <div className="space-y-1">
                <p className="text-sm text-foreground">Require human review before submission</p>
                <p className="text-xs text-muted-foreground">
                  Enforces human sign-off on submission workflows.
                </p>
              </div>
              <input
                aria-label="Human review required toggle"
                type="checkbox"
                checked={policyDraft?.require_human_review_for_submission ?? false}
                disabled={!trustCenter?.can_manage_policy || policySaving}
                onChange={(event) =>
                  onUpdateDraftBoolean("require_human_review_for_submission", event.target.checked)
                }
              />
            </label>

            <label className="flex items-start justify-between gap-3 rounded-md border border-border px-3 py-2">
              <div className="space-y-1">
                <p className="text-sm text-foreground">Share anonymized product telemetry</p>
                <p className="text-xs text-muted-foreground">
                  Shares anonymized usage metrics to improve platform reliability.
                </p>
              </div>
              <input
                aria-label="Anonymized telemetry toggle"
                type="checkbox"
                checked={policyDraft?.share_anonymized_product_telemetry ?? false}
                disabled={!trustCenter?.can_manage_policy || policySaving}
                onChange={(event) =>
                  onUpdateDraftBoolean("share_anonymized_product_telemetry", event.target.checked)
                }
              />
            </label>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label className="space-y-1 rounded-md border border-border px-3 py-2">
                <p className="text-sm text-foreground">Prompt log retention (days)</p>
                <input
                  aria-label="Prompt log retention days"
                  type="number"
                  min={0}
                  max={30}
                  value={policyDraft?.retain_prompt_logs_days ?? 0}
                  disabled={!trustCenter?.can_manage_policy || policySaving}
                  onChange={(event) =>
                    onUpdateDraftNumber(
                      "retain_prompt_logs_days",
                      Number.parseInt(event.target.value, 10) || 0
                    )
                  }
                  className="w-24 rounded-md border border-border bg-background px-2 py-1 text-sm"
                />
              </label>
              <label className="space-y-1 rounded-md border border-border px-3 py-2">
                <p className="text-sm text-foreground">Output log retention (days)</p>
                <input
                  aria-label="Output log retention days"
                  type="number"
                  min={0}
                  max={365}
                  value={policyDraft?.retain_output_logs_days ?? 30}
                  disabled={!trustCenter?.can_manage_policy || policySaving}
                  onChange={(event) =>
                    onUpdateDraftNumber(
                      "retain_output_logs_days",
                      Number.parseInt(event.target.value, 10) || 0
                    )
                  }
                  className="w-24 rounded-md border border-border bg-background px-2 py-1 text-sm"
                />
              </label>
            </div>

            {policyError ? <p className="text-xs text-destructive">{policyError}</p> : null}
            {policySavedMessage ? (
              <p className="text-xs text-emerald-600">{policySavedMessage}</p>
            ) : null}

            {trustCenter?.can_manage_policy ? (
              <Button type="submit" size="sm" disabled={policySaving || !unsavedPolicyChanges}>
                {policySaving ? "Saving..." : "Save policy controls"}
              </Button>
            ) : null}
          </form>
        </div>
      </CardContent>
    </Card>
  );
}
