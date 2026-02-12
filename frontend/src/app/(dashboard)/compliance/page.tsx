"use client";

import React, { useCallback, useEffect, useState } from "react";
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

export default function CompliancePage() {
  const [cmmc, setCmmc] = useState<CMMCStatus | null>(null);
  const [nist, setNist] = useState<NISTOverview | null>(null);
  const [privacy, setPrivacy] = useState<DataPrivacyInfo | null>(null);
  const [audit, setAudit] = useState<ComplianceAuditSummary | null>(null);
  const [readiness, setReadiness] = useState<ComplianceReadiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, n, p, a, r] = await Promise.all([
        complianceApi.getCMMCStatus(),
        complianceApi.getNISTOverview(),
        complianceApi.getDataPrivacy(),
        complianceApi.getComplianceAuditSummary(),
        complianceApi.getReadiness(),
      ]);
      setCmmc(c);
      setNist(n);
      setPrivacy(p);
      setAudit(a);
      setReadiness(r);
    } catch {
      setError("Failed to load compliance data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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
        <div className="flex justify-end">
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
