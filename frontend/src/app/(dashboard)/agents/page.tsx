"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { agentsApi, rfpApi } from "@/lib/api";
import type { AgentDescriptor, AgentRunResponse, RFPListItem } from "@/types";

const RUNNERS: Record<string, (rfpId: number) => Promise<AgentRunResponse>> = {
  research: (rfpId) => agentsApi.runResearch(rfpId),
  capture_planning: (rfpId) => agentsApi.runCapturePlanning(rfpId),
  proposal_prep: (rfpId) => agentsApi.runProposalPrep(rfpId),
  competitive_intel: (rfpId) => agentsApi.runCompetitiveIntel(rfpId),
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentDescriptor[]>([]);
  const [rfps, setRfps] = useState<RFPListItem[]>([]);
  const [selectedRfpId, setSelectedRfpId] = useState<number | null>(null);
  const [runningAgentId, setRunningAgentId] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, AgentRunResponse>>({});
  const [error, setError] = useState<string | null>(null);

  const selectedRfp = useMemo(
    () => rfps.find((item) => item.id === selectedRfpId) ?? null,
    [rfps, selectedRfpId]
  );

  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [catalog, opportunities] = await Promise.all([
        agentsApi.list(),
        rfpApi.list({ limit: 100 }),
      ]);
      setAgents(catalog);
      setRfps(opportunities);
      if (opportunities.length > 0) {
        setSelectedRfpId((current) => current ?? opportunities[0].id);
      }
    } catch {
      setError("Failed to load agents or opportunities.");
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const runAgent = async (agentId: string) => {
    if (!selectedRfpId) {
      setError("Select an opportunity before running an agent.");
      return;
    }

    const runner = RUNNERS[agentId];
    if (!runner) {
      setError("Unsupported agent.");
      return;
    }

    setRunningAgentId(agentId);
    setError(null);
    try {
      const result = await runner(selectedRfpId);
      setResults((prev) => ({ ...prev, [agentId]: result }));
    } catch {
      setError("Agent run failed.");
    } finally {
      setRunningAgentId(null);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Autonomous Agents"
        description="Run research, capture planning, proposal prep, and competitive intel automation"
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {error && <p className="text-sm text-destructive">{error}</p>}

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Target Opportunity</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <select
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              value={selectedRfpId ?? ""}
              onChange={(event) => setSelectedRfpId(Number(event.target.value) || null)}
            >
              {rfps.length === 0 && <option value="">No opportunities available</option>}
              {rfps.map((rfp) => (
                <option key={rfp.id} value={rfp.id}>
                  {rfp.title}
                </option>
              ))}
            </select>
            {selectedRfp && (
              <p className="text-xs text-muted-foreground">
                {selectedRfp.agency}
              </p>
            )}
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {agents.map((agent) => {
            const result = results[agent.id];
            const isRunning = runningAgentId === agent.id;
            return (
              <Card key={agent.id}>
                <CardHeader className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-base">{agent.name}</CardTitle>
                    <Badge variant="outline">{agent.id}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{agent.description}</p>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button
                    onClick={() => runAgent(agent.id)}
                    disabled={isRunning || !selectedRfpId}
                    className="w-full"
                  >
                    {isRunning ? "Running..." : "Run Agent"}
                  </Button>

                  {result && (
                    <div className="rounded-md border border-border p-3 space-y-2">
                      <p className="text-sm font-medium">Latest Run Summary</p>
                      <p className="text-xs text-muted-foreground">{result.summary}</p>
                      <div className="space-y-1">
                        {result.actions_taken.map((action) => (
                          <p key={action} className="text-xs text-muted-foreground">
                            - {action}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
