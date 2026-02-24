"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SOC2Readiness } from "@/types/compliance";
import { DomainBar } from "./DomainBar";

interface SOC2CardProps {
  soc2Readiness: SOC2Readiness | null;
}

export function SOC2Card({ soc2Readiness }: SOC2CardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>SOC 2 Type II Execution Track</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Program status</p>
            <p className="text-sm font-medium capitalize">
              {soc2Readiness?.status.replaceAll("_", " ") ?? "in progress"}
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Overall completion</p>
            <p className="text-sm font-medium">
              {soc2Readiness?.overall_percent_complete ?? 0}%
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Observation window</p>
            <p className="text-sm font-medium">
              {soc2Readiness
                ? `${new Date(soc2Readiness.observation_window_start).toLocaleDateString()} - ${new Date(soc2Readiness.observation_window_end).toLocaleDateString()}`
                : "Not scheduled"}
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Audit firm status</p>
            <p className="text-sm font-medium capitalize">
              {soc2Readiness?.audit_firm_status.replaceAll("_", " ") ?? "pending"}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <p className="text-sm font-medium">Trust Criteria Domains</p>
            {soc2Readiness?.domains.map((domain) => (
              <div key={domain.domain_id} className="space-y-1">
                <DomainBar
                  name={`${domain.domain_id} - ${domain.domain_name}`}
                  percentage={domain.percent_complete}
                />
                <p className="text-xs text-muted-foreground">
                  Owner: {domain.owner} · {domain.controls_ready}/{domain.controls_total} controls
                  ready
                </p>
              </div>
            ))}
          </div>
          <div className="space-y-3">
            <p className="text-sm font-medium">Milestones</p>
            {soc2Readiness?.milestones.map((milestone) => (
              <div
                key={milestone.milestone_id}
                className="rounded-lg border border-border p-3 space-y-1"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{milestone.title}</p>
                  <Badge variant="outline">{milestone.status.replaceAll("_", " ")}</Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Due {new Date(milestone.due_date).toLocaleDateString()} · Owner: {milestone.owner}
                </p>
                <p className="text-xs text-muted-foreground">{milestone.notes}</p>
                <Badge variant={milestone.evidence_ready ? "default" : "secondary"}>
                  {milestone.evidence_ready ? "Evidence ready" : "Evidence in progress"}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
