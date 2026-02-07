"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ResourceAllocation } from "@/types";

interface ResourceCardProps {
  data: ResourceAllocation | null;
  loading: boolean;
}

const STAGE_COLORS: Record<string, string> = {
  identified: "bg-gray-400",
  qualified: "bg-blue-400",
  pursuit: "bg-indigo-400",
  proposal: "bg-purple-400",
  submitted: "bg-yellow-400",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-400",
  in_progress: "bg-blue-400",
  review: "bg-yellow-400",
  final: "bg-green-400",
  submitted: "bg-emerald-400",
};

export function ResourceCard({ data, loading }: ResourceCardProps) {
  if (loading || !data) {
    return (
      <Card className="border border-border">
        <CardContent className="p-5">
          <div className="animate-pulse space-y-3">
            <div className="h-5 w-40 bg-muted rounded" />
            <div className="h-32 bg-muted rounded" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const totalCaptures = data.capture_workload.reduce((s, c) => s + c.count, 0);
  const totalProposals = data.proposal_workload.reduce((s, p) => s + p.count, 0);

  return (
    <Card className="border border-border">
      <CardContent className="p-5 space-y-5">
        <p className="text-sm font-medium text-foreground">Resource Allocation</p>

        {/* Capture Pipeline Workload */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-muted-foreground">
              Active Capture Pipeline
            </p>
            <Badge variant="outline" className="text-[10px]">
              {totalCaptures} total
            </Badge>
          </div>
          {data.capture_workload.length > 0 ? (
            <>
              <div className="flex h-4 rounded-full overflow-hidden bg-muted/50">
                {data.capture_workload.map((c) => {
                  const pct = totalCaptures > 0 ? (c.count / totalCaptures) * 100 : 0;
                  return (
                    <div
                      key={c.stage}
                      className={`${STAGE_COLORS[c.stage] || "bg-gray-300"}`}
                      style={{ width: `${pct}%` }}
                      title={`${c.stage}: ${c.count}`}
                    />
                  );
                })}
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {data.capture_workload.map((c) => (
                  <span key={c.stage} className="flex items-center gap-1 text-[10px] text-muted-foreground">
                    <span className={`w-2 h-2 rounded-full ${STAGE_COLORS[c.stage] || "bg-gray-300"}`} />
                    {c.stage} ({c.count})
                  </span>
                ))}
              </div>
            </>
          ) : (
            <p className="text-xs text-muted-foreground">No active captures</p>
          )}
        </div>

        {/* Proposal Workload */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-muted-foreground">Proposal Workload</p>
            <Badge variant="outline" className="text-[10px]">
              {totalProposals} total
            </Badge>
          </div>
          {data.proposal_workload.length > 0 ? (
            <>
              <div className="flex h-4 rounded-full overflow-hidden bg-muted/50">
                {data.proposal_workload.map((p) => {
                  const pct = totalProposals > 0 ? (p.count / totalProposals) * 100 : 0;
                  return (
                    <div
                      key={p.status}
                      className={`${STATUS_COLORS[p.status] || "bg-gray-300"}`}
                      style={{ width: `${pct}%` }}
                      title={`${p.status}: ${p.count}`}
                    />
                  );
                })}
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {data.proposal_workload.map((p) => (
                  <span key={p.status} className="flex items-center gap-1 text-[10px] text-muted-foreground">
                    <span className={`w-2 h-2 rounded-full ${STATUS_COLORS[p.status] || "bg-gray-300"}`} />
                    {p.status.replace("_", " ")} ({p.count})
                  </span>
                ))}
              </div>
            </>
          ) : (
            <p className="text-xs text-muted-foreground">No proposals</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
