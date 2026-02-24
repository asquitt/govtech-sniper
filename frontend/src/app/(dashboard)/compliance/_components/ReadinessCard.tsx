"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ComplianceReadiness } from "@/types/compliance";

interface ReadinessCardProps {
  readiness: ComplianceReadiness | null;
}

export function ReadinessCard({ readiness }: ReadinessCardProps) {
  return (
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
  );
}
