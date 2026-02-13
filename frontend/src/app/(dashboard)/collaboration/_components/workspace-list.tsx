"use client";

import React from "react";
import { Plus, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { SharedWorkspace } from "@/types";

interface WorkspaceListProps {
  workspaces: SharedWorkspace[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onCreate: () => void;
}

export function WorkspaceList({
  workspaces,
  selectedId,
  onSelect,
  onCreate,
}: WorkspaceListProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-foreground">Workspaces</h3>
        <Button size="sm" variant="outline" onClick={onCreate}>
          <Plus className="w-3 h-3 mr-1" /> New
        </Button>
      </div>
      {workspaces.length === 0 && (
        <p className="text-sm text-muted-foreground">No workspaces yet.</p>
      )}
      {workspaces.map((ws) => (
        <button
          key={ws.id}
          onClick={() => onSelect(ws.id)}
          className={`w-full text-left p-3 rounded-lg border transition-colors ${
            selectedId === ws.id
              ? "border-primary bg-primary/10"
              : "border-border hover:bg-secondary"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-foreground truncate">
              {ws.name}
            </span>
            <Badge variant="secondary" className="text-[10px]">
              <Users className="w-3 h-3 mr-1" />
              {ws.member_count}
            </Badge>
          </div>
          {ws.description && (
            <p className="text-xs text-muted-foreground mt-1 truncate">
              {ws.description}
            </p>
          )}
        </button>
      ))}
    </div>
  );
}
