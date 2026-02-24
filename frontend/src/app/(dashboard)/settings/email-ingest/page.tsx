"use client";

import React, { useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { collaborationApi } from "@/lib/api";
import { emailIngestApi } from "@/lib/api/email-ingest";
import { useAsyncData } from "@/hooks/use-async-data";
import type { SharedWorkspace } from "@/types";
import type { EmailIngestConfig, IngestedEmail } from "@/types/email-ingest";
import { AddConfigForm } from "./_components/AddConfigForm";
import { ConfigList } from "./_components/ConfigList";
import { EmailHistoryTable } from "./_components/EmailHistoryTable";

interface EmailIngestData {
  configs: EmailIngestConfig[];
  history: IngestedEmail[];
  historyTotal: number;
  workspaces: SharedWorkspace[];
}

export default function EmailIngestPage() {
  const { data, error: fetchError, refetch } = useAsyncData<EmailIngestData>(
    async () => {
      const [configsData, historyData, workspaceData] = await Promise.all([
        emailIngestApi.listConfigs(),
        emailIngestApi.listHistory({ limit: 50 }).catch(() => ({ items: [], total: 0 })),
        collaborationApi.listWorkspaces().catch(() => []),
      ]);
      return {
        configs: configsData,
        history: historyData.items,
        historyTotal: historyData.total,
        workspaces: workspaceData,
      };
    },
    [],
  );

  const configs = data?.configs ?? [];
  const history = data?.history ?? [];
  const historyTotal = data?.historyTotal ?? 0;
  const workspaces = data?.workspaces ?? [];
  const workspaceById = new Map(workspaces.map((workspace) => [workspace.id, workspace.name]));

  const [loading, setLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [testMsg, setTestMsg] = useState<string | null>(null);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  const error = fetchError ? fetchError.message : actionError;

  // Add config form
  const [showForm, setShowForm] = useState(false);
  const [imapServer, setImapServer] = useState("");
  const [imapPort, setImapPort] = useState("993");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [folder, setFolder] = useState("INBOX");
  const [workspaceId, setWorkspaceId] = useState("");
  const [autoCreateRfps, setAutoCreateRfps] = useState(true);
  const [minConfidence, setMinConfidence] = useState("0.35");

  const handleAddConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setActionError(null);
    try {
      const parsedConfidence = Number.parseFloat(minConfidence);
      await emailIngestApi.createConfig({
        imap_server: imapServer,
        imap_port: parseInt(imapPort, 10) || 993,
        email_address: email,
        password,
        folder: folder || "INBOX",
        workspace_id: workspaceId ? Number.parseInt(workspaceId, 10) : undefined,
        auto_create_rfps: autoCreateRfps,
        min_rfp_confidence:
          Number.isFinite(parsedConfidence) && parsedConfidence >= 0 && parsedConfidence <= 1
            ? parsedConfidence
            : 0.35,
      });
      setShowForm(false);
      setImapServer("");
      setImapPort("993");
      setEmail("");
      setPassword("");
      setFolder("INBOX");
      setWorkspaceId("");
      setAutoCreateRfps(true);
      setMinConfidence("0.35");
      await refetch();
    } catch {
      setActionError("Failed to create configuration.");
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (config: EmailIngestConfig) => {
    try {
      await emailIngestApi.updateConfig(config.id, {
        is_enabled: !config.is_enabled,
      });
      await refetch();
    } catch {
      setActionError("Failed to update configuration.");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await emailIngestApi.deleteConfig(id);
      await refetch();
    } catch {
      setActionError("Failed to delete configuration.");
    }
  };

  const handleTest = async (id: number) => {
    setTestMsg(null);
    try {
      const result = await emailIngestApi.testConnection(id);
      setTestMsg(result.message);
    } catch {
      setTestMsg("Connection test failed.");
    }
  };

  const handleReprocess = async (emailId: number) => {
    try {
      await emailIngestApi.reprocess(emailId);
      await refetch();
    } catch {
      setActionError("Failed to reprocess email.");
    }
  };

  const handleSyncNow = async () => {
    setSyncing(true);
    setActionError(null);
    setSyncMsg(null);
    try {
      const result = await emailIngestApi.syncNow({
        run_poll: true,
        run_process: true,
        poll_limit: 50,
        process_limit: 100,
      });
      setSyncMsg(
        `Sync complete: fetched ${result.fetched}, processed ${result.processed}, created ${result.created_rfps} opportunities.`,
      );
      await refetch();
    } catch {
      setActionError("Failed to run sync.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Email Ingestion"
        description="Configure IMAP accounts to automatically ingest RFP emails"
      />

      <div className="flex-1 p-6 overflow-auto space-y-6">
        {error && <p className="text-destructive text-sm">{error}</p>}
        {testMsg && <p className="text-sm text-muted-foreground">{testMsg}</p>}
        {syncMsg && <p className="text-sm text-muted-foreground">{syncMsg}</p>}

        <Card className="border border-border">
          <CardContent className="p-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-foreground">Ingestion Sync</p>
              <p className="text-xs text-muted-foreground">
                Pull unread mailbox items and process new opportunities now.
              </p>
            </div>
            <Button onClick={handleSyncNow} disabled={syncing}>
              {syncing ? "Syncing..." : "Run Sync Now"}
            </Button>
          </CardContent>
        </Card>

        {/* Configured accounts */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-foreground">
              Email Accounts
            </h2>
            <Button size="sm" onClick={() => setShowForm(!showForm)}>
              {showForm ? "Cancel" : "Add Account"}
            </Button>
          </div>

          {showForm && (
            <AddConfigForm
              imapServer={imapServer}
              imapPort={imapPort}
              email={email}
              password={password}
              folder={folder}
              workspaceId={workspaceId}
              autoCreateRfps={autoCreateRfps}
              minConfidence={minConfidence}
              workspaces={workspaces}
              loading={loading}
              onImapServerChange={setImapServer}
              onImapPortChange={setImapPort}
              onEmailChange={setEmail}
              onPasswordChange={setPassword}
              onFolderChange={setFolder}
              onWorkspaceIdChange={setWorkspaceId}
              onAutoCreateRfpsChange={setAutoCreateRfps}
              onMinConfidenceChange={setMinConfidence}
              onSubmit={handleAddConfig}
            />
          )}

          {configs.length === 0 && !showForm && (
            <p className="text-sm text-muted-foreground">
              No email accounts configured yet.
            </p>
          )}

          <ConfigList
            configs={configs}
            workspaceById={workspaceById}
            onToggle={handleToggle}
            onTest={handleTest}
            onDelete={handleDelete}
          />
        </div>

        {/* History table */}
        <EmailHistoryTable
          history={history}
          historyTotal={historyTotal}
          onReprocess={handleReprocess}
        />
      </div>
    </div>
  );
}
