"use client";

import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Bot, Play } from "lucide-react";
import { dashApi } from "@/lib/api";
import { AgentProgress } from "./agent-progress";

interface AgentInfo {
  type: string;
  description: string;
}

interface AgentRunResult {
  run_id: string;
  agent_type: string;
  status: string;
  result: Record<string, unknown>;
}

interface AgentLauncherProps {
  selectedRfpId: number | null;
}

export function AgentLauncher({ selectedRfpId }: AgentLauncherProps) {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [runningAgent, setRunningAgent] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<AgentRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        setIsLoadingAgents(true);
        const response = await dashApi.listAgents();
        setAgents(response.agents);
      } catch (err) {
        console.error("Failed to load agents", err);
        setError("Failed to load agents.");
      } finally {
        setIsLoadingAgents(false);
      }
    };
    fetchAgents();
  }, []);

  const handleRunAgent = async (agentType: string) => {
    setRunningAgent(agentType);
    setError(null);
    setLastResult(null);
    try {
      const result = await dashApi.runAgent(
        agentType,
        selectedRfpId ?? undefined
      );
      setLastResult(result);
    } catch (err) {
      console.error("Agent run failed", err);
      setError(`Agent "${agentType}" failed to run.`);
    } finally {
      setRunningAgent(null);
    }
  };

  const agentLabel = (type: string) =>
    type
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");

  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-primary" />
          <p className="text-sm font-semibold text-foreground">AI Agents</p>
          {isLoadingAgents && <Loader2 className="w-3 h-3 animate-spin" />}
        </div>
        <p className="text-xs text-muted-foreground">
          Launch autonomous agents to research, capture, or prepare proposals.
          {!selectedRfpId && " Select an opportunity above for best results."}
        </p>

        {error && <p className="text-xs text-destructive">{error}</p>}

        <div className="flex flex-wrap gap-2">
          {agents.map((agent) => (
            <Button
              key={agent.type}
              variant="outline"
              size="sm"
              disabled={runningAgent !== null}
              onClick={() => handleRunAgent(agent.type)}
              className="gap-1"
            >
              {runningAgent === agent.type ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Play className="w-3 h-3" />
              )}
              {agentLabel(agent.type)}
            </Button>
          ))}
        </div>

        {agents.length > 0 && !isLoadingAgents && (
          <div className="space-y-1">
            {agents.map((agent) => (
              <div key={agent.type} className="flex items-start gap-2">
                <Badge variant="secondary" className="text-[10px] shrink-0 mt-0.5">
                  {agentLabel(agent.type)}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {agent.description}
                </span>
              </div>
            ))}
          </div>
        )}

        {lastResult && <AgentProgress result={lastResult} />}
      </CardContent>
    </Card>
  );
}
