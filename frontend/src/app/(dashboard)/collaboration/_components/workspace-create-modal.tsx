"use client";

import React from "react";
import { Button } from "@/components/ui/button";

interface WorkspaceCreateModalProps {
  newName: string;
  newDesc: string;
  onNewNameChange: (name: string) => void;
  onNewDescChange: (desc: string) => void;
  onCreate: () => void;
  onCancel: () => void;
}

export function WorkspaceCreateModal({
  newName,
  newDesc,
  onNewNameChange,
  onNewDescChange,
  onCreate,
  onCancel,
}: WorkspaceCreateModalProps) {
  return (
    <div className="mb-6 p-4 rounded-lg border border-primary/30 bg-primary/5">
      <h3 className="text-sm font-semibold text-foreground mb-3">
        Create Workspace
      </h3>
      <div className="space-y-3">
        <input
          className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          placeholder="Workspace name"
          value={newName}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => onNewNameChange(e.target.value)}
        />
        <input
          className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          placeholder="Description (optional)"
          value={newDesc}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => onNewDescChange(e.target.value)}
        />
        <div className="flex gap-2">
          <Button size="sm" onClick={onCreate} disabled={!newName.trim()}>
            Create
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={onCancel}
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
