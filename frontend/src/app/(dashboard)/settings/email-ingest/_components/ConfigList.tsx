"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { EmailIngestConfig } from "@/types/email-ingest";

interface ConfigListProps {
  configs: EmailIngestConfig[];
  workspaceById: Map<number, string>;
  onToggle: (config: EmailIngestConfig) => void;
  onTest: (id: number) => void;
  onDelete: (id: number) => void;
}

export function ConfigList({
  configs,
  workspaceById,
  onToggle,
  onTest,
  onDelete,
}: ConfigListProps) {
  return (
    <div className="space-y-2">
      {configs.map((config) => (
        <Card key={config.id} className="border border-border">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground">
                {config.email_address}
              </p>
              <p className="text-xs text-muted-foreground">
                {config.imap_server}:{config.imap_port} / {config.folder}
              </p>
              <p className="text-xs text-muted-foreground">
                Workspace:{" "}
                {config.workspace_id
                  ? (workspaceById.get(config.workspace_id) ?? `#${config.workspace_id}`)
                  : "none"}
                {" · "}
                Auto-create: {config.auto_create_rfps ? "enabled" : "disabled"}
                {" · "}
                Threshold: {config.min_rfp_confidence.toFixed(2)}
              </p>
              {config.last_checked_at && (
                <p className="text-xs text-muted-foreground">
                  Last checked:{" "}
                  {new Date(config.last_checked_at).toLocaleString()}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Badge
                variant={config.is_enabled ? "success" : "outline"}
                className="cursor-pointer"
                onClick={() => onToggle(config)}
              >
                {config.is_enabled ? "Enabled" : "Disabled"}
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onTest(config.id)}
              >
                Test
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive"
                onClick={() => onDelete(config.id)}
              >
                Delete
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
