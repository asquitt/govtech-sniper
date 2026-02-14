"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { complianceApi } from "@/lib/api/compliance";
import type {
  CMMCStatus,
  NISTOverview,
  DataPrivacyInfo,
  ComplianceAuditSummary,
  ComplianceReadiness,
  TrustCenterPolicy,
  TrustCenterProfile,
} from "@/types/compliance";

function ScoreRing({ score }: { score: number }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 70 ? "text-green-500" : score >= 40 ? "text-yellow-500" : "text-red-500";

  return (
    <div className="relative w-36 h-36">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 128 128">
        <circle cx="64" cy="64" r={radius} fill="none" stroke="currentColor"
          className="text-muted/30" strokeWidth="10" />
        <circle cx="64" cy="64" r={radius} fill="none" stroke="currentColor"
          className={color} strokeWidth="10" strokeDasharray={circumference}
          strokeDashoffset={offset} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold">{score}%</span>
        <span className="text-xs text-muted-foreground">Compliance</span>
      </div>
    </div>
  );
}

function DomainBar({ name, percentage }: { name: string; percentage: number }) {
  const color = percentage >= 70 ? "bg-green-500" : percentage >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="truncate mr-2">{name}</span>
        <span className="font-medium flex-shrink-0">{percentage}%</span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

function trustStatusClass(status: "enforced" | "warning" | "configured"): string {
  if (status === "enforced") {
    return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  }
  if (status === "warning") {
    return "bg-destructive/10 text-destructive";
  }
  return "bg-primary/10 text-primary";
}

function hasPolicyChanges(a: TrustCenterPolicy | null, b: TrustCenterPolicy | null): boolean {
  if (!a || !b) return false;
  return (
    a.allow_ai_requirement_analysis !== b.allow_ai_requirement_analysis ||
    a.allow_ai_draft_generation !== b.allow_ai_draft_generation ||
    a.require_human_review_for_submission !== b.require_human_review_for_submission ||
    a.share_anonymized_product_telemetry !== b.share_anonymized_product_telemetry ||
    a.retain_prompt_logs_days !== b.retain_prompt_logs_days ||
    a.retain_output_logs_days !== b.retain_output_logs_days
  );
}

export default function CompliancePage() {
  const [cmmc, setCmmc] = useState<CMMCStatus | null>(null);
  const [nist, setNist] = useState<NISTOverview | null>(null);
  const [privacy, setPrivacy] = useState<DataPrivacyInfo | null>(null);
  const [audit, setAudit] = useState<ComplianceAuditSummary | null>(null);
  const [readiness, setReadiness] = useState<ComplianceReadiness | null>(null);
  const [trustCenter, setTrustCenter] = useState<TrustCenterProfile | null>(null);
  const [policyDraft, setPolicyDraft] = useState<TrustCenterPolicy | null>(null);
  const [policySaving, setPolicySaving] = useState(false);
  const [evidenceExporting, setEvidenceExporting] = useState(false);
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [policySavedMessage, setPolicySavedMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, n, p, a, r, t] = await Promise.all([
        complianceApi.getCMMCStatus(),
        complianceApi.getNISTOverview(),
        complianceApi.getDataPrivacy(),
        complianceApi.getComplianceAuditSummary(),
        complianceApi.getReadiness(),
        complianceApi.getTrustCenter(),
      ]);
      setCmmc(c);
      setNist(n);
      setPrivacy(p);
      setAudit(a);
      setReadiness(r);
      setTrustCenter(t);
      setPolicyDraft(t.policy);
    } catch {
      setError("Failed to load compliance data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const unsavedPolicyChanges = useMemo(() => {
    return hasPolicyChanges(trustCenter?.policy ?? null, policyDraft);
  }, [trustCenter, policyDraft]);

  const updateDraftBoolean = (
    key:
      | "allow_ai_requirement_analysis"
      | "allow_ai_draft_generation"
      | "require_human_review_for_submission"
      | "share_anonymized_product_telemetry",
    value: boolean
  ) => {
    setPolicyDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
    setPolicySavedMessage(null);
  };

  const updateDraftNumber = (
    key: "retain_prompt_logs_days" | "retain_output_logs_days",
    value: number
  ) => {
    const clamped = key === "retain_prompt_logs_days"
      ? Math.max(0, Math.min(30, value))
      : Math.max(0, Math.min(365, value));
    setPolicyDraft((prev) => (prev ? { ...prev, [key]: clamped } : prev));
    setPolicySavedMessage(null);
  };

  const handleTrustPolicySave = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!policyDraft || !trustCenter?.can_manage_policy) {
      return;
    }
    setPolicySaving(true);
    setPolicyError(null);
    setPolicySavedMessage(null);
    try {
      const updated = await complianceApi.updateTrustCenterPolicy(policyDraft);
      setTrustCenter(updated);
      setPolicyDraft(updated.policy);
      setPolicySavedMessage("Trust center policy saved.");
    } catch {
      setPolicyError("Failed to update trust-center policy.");
    } finally {
      setPolicySaving(false);
    }
  };

  const handleTrustEvidenceExport = async () => {
    setEvidenceExporting(true);
    setPolicyError(null);
    try {
      const blob = await complianceApi.exportTrustCenterEvidence();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `trust_center_evidence_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch {
      setPolicyError("Failed to export trust-center evidence.");
    } finally {
      setEvidenceExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Compliance Dashboard" description="CMMC, NIST 800-53, and data privacy posture" />
        <div className="flex-1 p-6">
          <div className="animate-pulse space-y-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-40 bg-muted rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header title="Compliance Dashboard" description="CMMC, NIST 800-53, and data privacy posture" />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        <div className="flex flex-wrap justify-end gap-2">
          <Link href="/trust-center" target="_blank">
            <Button variant="outline" size="sm">
              Public Trust Center ↗
            </Button>
          </Link>
          <Link href="/compliance/timeline">
            <Button variant="outline" size="sm">
              View Compliance Roadmap &rarr;
            </Button>
          </Link>
        </div>

        {error && (
          <div className="bg-destructive/10 text-destructive rounded-lg p-4">
            {error}
          </div>
        )}

        {/* Top score cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="flex flex-col items-center py-6">
            <ScoreRing score={cmmc?.score_percentage ?? 0} />
            <p className="mt-3 font-semibold">CMMC Level {cmmc?.target_level ?? 2} Readiness</p>
            <p className="text-sm text-muted-foreground">
              {cmmc?.met_controls ?? 0} / {cmmc?.total_controls ?? 0} controls met
            </p>
          </Card>

          <Card className="flex flex-col items-center py-6">
            <ScoreRing score={nist?.overall_coverage ?? 0} />
            <p className="mt-3 font-semibold">NIST 800-53 Coverage</p>
            <p className="text-sm text-muted-foreground">
              {nist?.total_families ?? 0} control families tracked
            </p>
          </Card>

          <Card className="flex flex-col items-center py-6">
            <ScoreRing score={audit?.compliance_score ?? 0} />
            <p className="mt-3 font-semibold">Overall Compliance</p>
            <p className="text-sm text-muted-foreground">
              {audit?.events_last_30_days ?? 0} audit events (30 days)
            </p>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>AI & Data Trust Center</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
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
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={evidenceExporting}
                onClick={handleTrustEvidenceExport}
              >
                {evidenceExporting ? "Exporting..." : "Export Trust Evidence JSON"}
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
              <form className="space-y-3" onSubmit={handleTrustPolicySave}>
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
                      updateDraftBoolean("allow_ai_requirement_analysis", event.target.checked)
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
                      updateDraftBoolean("allow_ai_draft_generation", event.target.checked)
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
                      updateDraftBoolean("require_human_review_for_submission", event.target.checked)
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
                      updateDraftBoolean("share_anonymized_product_telemetry", event.target.checked)
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
                        updateDraftNumber(
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
                        updateDraftNumber(
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

        {/* CMMC Domain Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle>CMMC Level 2 Domain Readiness</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
              {cmmc?.domains.map((d) => (
                <DomainBar key={d.domain} name={d.domain_name} percentage={d.percentage} />
              ))}
            </div>
          </CardContent>
        </Card>

        {/* NIST Families Grid */}
        <Card>
          <CardHeader>
            <CardTitle>NIST 800-53 Rev 5 Control Families</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {nist?.families.map((f) => {
                const pct = f.total_controls > 0
                  ? Math.round((f.implemented / f.total_controls) * 100)
                  : 0;
                return (
                  <div key={f.family_id} className="border rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{f.family_id}</span>
                      <Badge variant={pct >= 50 ? "default" : "secondary"}>{pct}%</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{f.name}</p>
                    <div className="flex gap-1 text-[10px]">
                      <span className="text-green-600">{f.implemented} impl</span>
                      <span className="text-muted-foreground">|</span>
                      <span className="text-yellow-600">{f.partial} partial</span>
                      <span className="text-muted-foreground">|</span>
                      <span className="text-red-500">{f.not_implemented} gap</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Data Privacy + Audit Summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Data Privacy Practices</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {privacy && (
                <>
                  <PrivacySection title="Data Handling" items={privacy.data_handling} />
                  <PrivacySection title="Encryption" items={privacy.encryption} />
                  <PrivacySection title="Access Controls" items={privacy.access_controls} />
                  <PrivacySection title="Data Retention" items={privacy.data_retention} />
                  <div>
                    <p className="text-sm font-medium mb-1">Certifications</p>
                    <div className="flex flex-wrap gap-2">
                      {privacy.certifications.map((c) => (
                        <Badge key={c} variant="outline">{c}</Badge>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Audit Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="border rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold">{audit?.total_events ?? 0}</p>
                  <p className="text-xs text-muted-foreground">Total Events</p>
                </div>
                <div className="border rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold">{audit?.events_last_30_days ?? 0}</p>
                  <p className="text-xs text-muted-foreground">Last 30 Days</p>
                </div>
              </div>
              {audit && Object.keys(audit.by_type).length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-2">Events by Type</p>
                  <div className="space-y-2">
                    {Object.entries(audit.by_type)
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 10)
                      .map(([action, count]) => (
                        <div key={action} className="flex justify-between text-sm">
                          <span className="text-muted-foreground truncate mr-2">{action}</span>
                          <span className="font-medium">{count}</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
              {audit && Object.keys(audit.by_type).length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No audit events recorded in the last 30 days.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Certification and Listing Readiness</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {readiness?.programs.map((program) => (
              <div key={program.id} className="rounded-lg border border-border p-3 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{program.name}</p>
                  <Badge variant="outline">{program.status.replaceAll("_", " ")}</Badge>
                </div>
                <div className="h-2 rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${program.percent_complete}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Next: {program.next_milestone}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function PrivacySection({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-sm font-medium mb-1">{title}</p>
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item} className="text-xs text-muted-foreground flex items-start gap-2">
            <span className="mt-1.5 w-1 h-1 rounded-full bg-primary flex-shrink-0" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
