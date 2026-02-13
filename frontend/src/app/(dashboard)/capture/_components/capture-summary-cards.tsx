"use client";

import { Card, CardContent } from "@/components/ui/card";

interface CaptureSummaryCardsProps {
  totalOpportunities: number;
  capturePlans: number;
  pendingDecisions: number;
}

export function CaptureSummaryCards({
  totalOpportunities,
  capturePlans,
  pendingDecisions,
}: CaptureSummaryCardsProps) {
  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">Total Opportunities</p>
          <p className="text-2xl font-bold text-primary">{totalOpportunities}</p>
        </CardContent>
      </Card>
      <Card className="bg-gradient-to-br from-accent/5 to-accent/10 border-accent/20">
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">Capture Plans</p>
          <p className="text-2xl font-bold text-accent">{capturePlans}</p>
        </CardContent>
      </Card>
      <Card className="bg-gradient-to-br from-warning/5 to-warning/10 border-warning/20">
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground">Pending Decisions</p>
          <p className="text-2xl font-bold text-warning">{pendingDecisions}</p>
        </CardContent>
      </Card>
    </div>
  );
}
