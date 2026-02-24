"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { WorkflowExecution } from "@/types/workflow";

export interface ExecutionHistoryProps {
  executions: WorkflowExecution[];
}

export function ExecutionHistory({ executions }: ExecutionHistoryProps) {
  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-foreground">Recent Executions</p>
      {executions.length === 0 ? (
        <p className="text-xs text-muted-foreground">No executions yet.</p>
      ) : (
        <Card className="border border-border">
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-2 font-medium text-muted-foreground">Rule</th>
                  <th className="text-left px-4 py-2 font-medium text-muted-foreground">Entity</th>
                  <th className="text-left px-4 py-2 font-medium text-muted-foreground">Status</th>
                  <th className="text-left px-4 py-2 font-medium text-muted-foreground">Triggered</th>
                </tr>
              </thead>
              <tbody>
                {executions.map((ex) => (
                  <tr key={ex.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-2">Rule #{ex.rule_id}</td>
                    <td className="px-4 py-2">{ex.entity_type} #{ex.entity_id}</td>
                    <td className="px-4 py-2">
                      <Badge
                        variant={
                          ex.status === "success" ? "success" : ex.status === "failed" ? "destructive" : "outline"
                        }
                      >
                        {ex.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {new Date(ex.triggered_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
