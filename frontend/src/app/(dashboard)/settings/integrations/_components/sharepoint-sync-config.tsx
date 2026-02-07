"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  CheckCircle2,
  Cloud,
  Loader2,
  Play,
  Trash2,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { sharepointSyncApi } from "@/lib/api/sharepoint-sync";
import type {
  SharePointSyncConfig,
  SharePointSyncLog,
  SyncDirection,
} from "@/types/sharepoint-sync";

interface SharePointSyncConfigPanelProps {
  proposalId: number;
}

export function SharePointSyncConfigPanel({
  proposalId,
}: SharePointSyncConfigPanelProps) {
  const [config, setConfig] = useState<SharePointSyncConfig | null>(null);
  const [logs, setLogs] = useState<SharePointSyncLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // Form state
  const [folder, setFolder] = useState("/Proposals");
  const [direction, setDirection] = useState<SyncDirection>("push");
  const [autoSync, setAutoSync] = useState(false);
  const [watchRfps, setWatchRfps] = useState(false);

  const loadConfig = useCallback(async () => {
    setIsLoading(true);
    try {
      const configs = await sharepointSyncApi.listConfigs(proposalId);
      if (configs.length > 0) {
        const c = configs[0];
        setConfig(c);
        setFolder(c.sharepoint_folder);
        setDirection(c.sync_direction);
        setAutoSync(c.auto_sync_enabled);
        setWatchRfps(c.watch_for_rfps);
        // Load logs
        const syncLogs = await sharepointSyncApi.getSyncStatus(c.id, 10);
        setLogs(syncLogs);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load config");
    } finally {
      setIsLoading(false);
    }
  }, [proposalId]);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setMessage(null);
    try {
      const result = await sharepointSyncApi.configure({
        proposal_id: proposalId,
        sharepoint_folder: folder,
        sync_direction: direction,
        auto_sync_enabled: autoSync,
        watch_for_rfps: watchRfps,
      });
      setConfig(result);
      setMessage("Configuration saved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSync = async () => {
    if (!config) return;
    setIsSyncing(true);
    setError(null);
    setMessage(null);
    try {
      await sharepointSyncApi.triggerSync(config.id);
      setMessage("Sync triggered — check logs for status");
      // Reload logs after a brief delay
      setTimeout(async () => {
        const syncLogs = await sharepointSyncApi.getSyncStatus(config.id, 10);
        setLogs(syncLogs);
      }, 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync trigger failed");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleDelete = async () => {
    if (!config) return;
    try {
      await sharepointSyncApi.deleteConfig(config.id);
      setConfig(null);
      setLogs([]);
      setFolder("/Proposals");
      setDirection("push");
      setAutoSync(false);
      setWatchRfps(false);
      setMessage("Configuration deleted");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center gap-2">
          <Cloud className="w-4 h-4 text-primary" />
          <p className="text-sm font-semibold">SharePoint Sync</p>
        </div>

        {/* Form */}
        <div className="space-y-3">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">
              SharePoint Folder
            </label>
            <input
              className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
              value={folder}
              onChange={(e) => setFolder(e.target.value)}
              placeholder="/Proposals"
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground block mb-1">
              Sync Direction
            </label>
            <select
              className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
              value={direction}
              onChange={(e) => setDirection(e.target.value as SyncDirection)}
            >
              <option value="push">Push (to SharePoint)</option>
              <option value="pull">Pull (from SharePoint)</option>
              <option value="bidirectional">Bidirectional</option>
            </select>
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-1.5 text-xs">
              <input
                type="checkbox"
                checked={autoSync}
                onChange={(e) => setAutoSync(e.target.checked)}
                className="rounded"
              />
              Auto-sync
            </label>
            <label className="flex items-center gap-1.5 text-xs">
              <input
                type="checkbox"
                checked={watchRfps}
                onChange={(e) => setWatchRfps(e.target.checked)}
                className="rounded"
              />
              Watch for RFPs
            </label>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            size="sm"
            className="flex-1 text-xs"
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <CheckCircle2 className="w-3 h-3" />
            )}
            {config ? "Update" : "Configure"}
          </Button>
          {config && (
            <>
              <Button
                size="sm"
                variant="outline"
                className="text-xs"
                onClick={handleSync}
                disabled={isSyncing}
              >
                {isSyncing ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Play className="w-3 h-3" />
                )}
                Sync Now
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="text-xs text-red-500 hover:text-red-600"
                onClick={handleDelete}
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </>
          )}
        </div>

        {/* Status messages */}
        {error && (
          <p className="text-xs text-red-500 bg-red-500/10 border border-red-500/30 rounded-md px-2 py-1.5">
            {error}
          </p>
        )}
        {message && (
          <p className="text-xs text-green-600 bg-green-500/10 border border-green-500/30 rounded-md px-2 py-1.5">
            {message}
          </p>
        )}

        {/* Last synced */}
        {config?.last_synced_at && (
          <p className="text-[10px] text-muted-foreground">
            Last synced: {new Date(config.last_synced_at).toLocaleString()}
          </p>
        )}

        {/* Sync logs */}
        {logs.length > 0 && (
          <div className="space-y-1">
            <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">
              Recent Sync History
            </p>
            {logs.map((log) => (
              <div
                key={log.id}
                className="flex items-center gap-1.5 text-[11px]"
              >
                {log.status === "success" ? (
                  <CheckCircle2 className="w-3 h-3 text-green-500 shrink-0" />
                ) : (
                  <XCircle className="w-3 h-3 text-red-500 shrink-0" />
                )}
                <span className="text-muted-foreground">{log.action}</span>
                <span className="text-muted-foreground ml-auto">
                  {new Date(log.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
