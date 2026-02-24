"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { GovCloudDeploymentProfile } from "@/types/compliance";

interface GovCloudCardProps {
  govCloudProfile: GovCloudDeploymentProfile | null;
}

export function GovCloudCard({ govCloudProfile }: GovCloudCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>GovCloud Deployment Profile</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Cloud provider</p>
            <p className="text-sm font-medium">{govCloudProfile?.provider ?? "AWS GovCloud (US)"}</p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Deployment status</p>
            <p className="text-sm font-medium capitalize">
              {govCloudProfile?.status.replaceAll("_", " ") ?? "in progress"}
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs text-muted-foreground">Target regions</p>
            <p className="text-sm font-medium">
              {govCloudProfile?.target_regions.join(", ") ?? "us-gov-west-1, us-gov-east-1"}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <p className="text-sm font-medium">Boundary Services</p>
            <ul className="space-y-1">
              {(govCloudProfile?.boundary_services ?? []).map((service) => (
                <li key={service} className="text-xs text-muted-foreground flex items-start gap-2">
                  <span className="mt-1.5 w-1 h-1 rounded-full bg-primary flex-shrink-0" />
                  {service}
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Control Status</p>
            <p className="text-xs text-muted-foreground">
              Identity federation: {govCloudProfile?.identity_federation_status.replaceAll("_", " ")}
            </p>
            <p className="text-xs text-muted-foreground">
              Network isolation: {govCloudProfile?.network_isolation_status.replaceAll("_", " ")}
            </p>
            <p className="text-xs text-muted-foreground">
              Data residency: {govCloudProfile?.data_residency_status.replaceAll("_", " ")}
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-sm font-medium">Migration Phases</p>
          {govCloudProfile?.migration_phases.map((phase) => (
            <div key={phase.phase_id} className="rounded-lg border border-border p-3 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium">{phase.title}</p>
                <Badge variant="outline">{phase.status.replaceAll("_", " ")}</Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Target {new Date(phase.target_date).toLocaleDateString()} · Owner: {phase.owner}
              </p>
              <ul className="space-y-1">
                {phase.exit_criteria.map((criterion) => (
                  <li key={criterion} className="text-xs text-muted-foreground flex items-start gap-2">
                    <span className="mt-1.5 w-1 h-1 rounded-full bg-primary flex-shrink-0" />
                    {criterion}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
