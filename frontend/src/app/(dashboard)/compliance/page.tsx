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
  ComplianceReadinessCheckpointSnapshot,
  ComplianceTrustMetrics,
  GovCloudDeploymentProfile,
  SOC2Readiness,
  TrustCenterPolicy,
  TrustCenterProfile,
} from "@/types/compliance";
import { ScoreRing } from "./_components/ScoreRing";
import { DomainBar } from "./_components/DomainBar";
import { TrustCenterCard } from "./_components/TrustCenterCard";
import { SOC2Card } from "./_components/SOC2Card";
import { GovCloudCard } from "./_components/GovCloudCard";
import { ReadinessCard } from "./_components/ReadinessCard";
import { CheckpointsCard } from "./_components/CheckpointsCard";
import { PrivacySection } from "./_components/PrivacySection";

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
  const [readinessCheckpoints, setReadinessCheckpoints] =
    useState<ComplianceReadinessCheckpointSnapshot | null>(null);
  const [trustMetrics, setTrustMetrics] = useState<ComplianceTrustMetrics | null>(null);
  const [govCloudProfile, setGovCloudProfile] = useState<GovCloudDeploymentProfile | null>(null);
  const [soc2Readiness, setSoc2Readiness] = useState<SOC2Readiness | null>(null);
  const [trustCenter, setTrustCenter] = useState<TrustCenterProfile | null>(null);
  const [policyDraft, setPolicyDraft] = useState<TrustCenterPolicy | null>(null);
  const [policySaving, setPolicySaving] = useState(false);
  const [evidenceExporting, setEvidenceExporting] = useState(false);
  const [threePaoExporting, setThreePaoExporting] = useState(false);
  const [trustExportFormat, setTrustExportFormat] = useState<"json" | "csv" | "pdf">("json");
  const [signedTrustExports, setSignedTrustExports] = useState(false);
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [policySavedMessage, setPolicySavedMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, n, p, a, r, rc, tm, g, s, t] = await Promise.all([
        complianceApi.getCMMCStatus(),
        complianceApi.getNISTOverview(),
        complianceApi.getDataPrivacy(),
        complianceApi.getComplianceAuditSummary(),
        complianceApi.getReadiness(),
        complianceApi.getReadinessCheckpoints(),
        complianceApi.getTrustMetrics(),
        complianceApi.getGovCloudProfile(),
        complianceApi.getSOC2Readiness(),
        complianceApi.getTrustCenter(),
      ]);
      setCmmc(c);
      setNist(n);
      setPrivacy(p);
      setAudit(a);
      setReadiness(r);
      setReadinessCheckpoints(rc);
      setTrustMetrics(tm);
      setGovCloudProfile(g);
      setSoc2Readiness(s);
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
      const blob = await complianceApi.exportTrustCenterEvidenceWithOptions({
        format: trustExportFormat,
        signed: signedTrustExports,
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `trust_center_evidence_${new Date().toISOString().slice(0, 10)}.${trustExportFormat}`;
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

  const handleThreePaoExport = async () => {
    setThreePaoExporting(true);
    setPolicyError(null);
    try {
      const blob = await complianceApi.exportThreePAOPackage({
        signed: signedTrustExports,
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `three_pao_readiness_package_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch {
      setPolicyError("Failed to export 3PAO readiness package.");
    } finally {
      setThreePaoExporting(false);
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
          <Link href="/compliance/evidence-registry">
            <Button variant="outline" size="sm">
              Evidence Registry
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

        <TrustCenterCard
          trustCenter={trustCenter}
          trustMetrics={trustMetrics}
          policyDraft={policyDraft}
          policySaving={policySaving}
          policyError={policyError}
          policySavedMessage={policySavedMessage}
          unsavedPolicyChanges={unsavedPolicyChanges}
          trustExportFormat={trustExportFormat}
          signedTrustExports={signedTrustExports}
          evidenceExporting={evidenceExporting}
          threePaoExporting={threePaoExporting}
          onTrustExportFormatChange={setTrustExportFormat}
          onSignedTrustExportsChange={setSignedTrustExports}
          onTrustEvidenceExport={handleTrustEvidenceExport}
          onThreePaoExport={handleThreePaoExport}
          onPolicySave={handleTrustPolicySave}
          onUpdateDraftBoolean={updateDraftBoolean}
          onUpdateDraftNumber={updateDraftNumber}
        />

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

        <SOC2Card soc2Readiness={soc2Readiness} />
        <GovCloudCard govCloudProfile={govCloudProfile} />
        <ReadinessCard readiness={readiness} />
        <CheckpointsCard readinessCheckpoints={readinessCheckpoints} />
      </div>
    </div>
  );
}
