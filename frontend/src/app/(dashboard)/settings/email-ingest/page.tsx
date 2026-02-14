"use client";

import React, { useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { collaborationApi } from "@/lib/api";
import { emailIngestApi } from "@/lib/api/email-ingest";
import { useAsyncData } from "@/hooks/use-async-data";
import type { SharedWorkspace } from "@/types";
import type { EmailIngestConfig, IngestedEmail } from "@/types/email-ingest";

const INPUT_CLASS =
  "rounded-md border border-border bg-background px-3 py-2 text-sm w-full";

export default function EmailIngestPage() {
  interface EmailIngestData {
    configs: EmailIngestConfig[];
    history: IngestedEmail[];
    historyTotal: number;
    workspaces: SharedWorkspace[];
  }

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

  const statusVariant = (
    status: IngestedEmail["processing_status"]
  ): "default" | "success" | "destructive" | "outline" => {
    switch (status) {
      case "processed":
        return "success";
      case "error":
        return "destructive";
      case "ignored":
        return "outline";
      default:
        return "default";
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
            <Card className="border border-border">
              <CardContent className="p-4">
                <form onSubmit={handleAddConfig} className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground" htmlFor="imap-server">
                        IMAP Server
                      </label>
                      <input
                        id="imap-server"
                        className={INPUT_CLASS}
                        placeholder="imap.gmail.com"
                        value={imapServer}
                        onChange={(e) => setImapServer(e.target.value)}
                        required
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground" htmlFor="imap-port">
                        IMAP Port
                      </label>
                      <input
                        id="imap-port"
                        className={INPUT_CLASS}
                        placeholder="993"
                        type="number"
                        value={imapPort}
                        onChange={(e) => setImapPort(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground" htmlFor="email-address">
                        Email Address
                      </label>
                      <input
                        id="email-address"
                        className={INPUT_CLASS}
                        placeholder="capture@example.com"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground" htmlFor="email-password">
                        App Password
                      </label>
                      <input
                        id="email-password"
                        className={INPUT_CLASS}
                        placeholder="Password / App password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground" htmlFor="email-folder">
                        Folder
                      </label>
                      <input
                        id="email-folder"
                        className={INPUT_CLASS}
                        placeholder="INBOX"
                        value={folder}
                        onChange={(e) => setFolder(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground" htmlFor="workspace-routing">
                        Team Workspace (Optional)
                      </label>
                      <select
                        id="workspace-routing"
                        className={INPUT_CLASS}
                        value={workspaceId}
                        onChange={(e) => setWorkspaceId(e.target.value)}
                      >
                        <option value="">No routing workspace</option>
                        {workspaces.map((workspace) => (
                          <option key={workspace.id} value={workspace.id}>
                            {workspace.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="flex items-center gap-2 text-sm text-foreground">
                      <input
                        type="checkbox"
                        checked={autoCreateRfps}
                        onChange={(e) => setAutoCreateRfps(e.target.checked)}
                      />
                      Auto-create opportunities for qualified emails
                    </label>
                    <div className="space-y-1">
                      <label
                        className="text-xs text-muted-foreground"
                        htmlFor="confidence-threshold"
                      >
                        Minimum RFP Confidence (0-1)
                      </label>
                      <input
                        id="confidence-threshold"
                        className={INPUT_CLASS}
                        type="number"
                        min="0"
                        max="1"
                        step="0.05"
                        value={minConfidence}
                        onChange={(e) => setMinConfidence(e.target.value)}
                      />
                    </div>
                  </div>
                  <Button type="submit" disabled={loading}>
                    {loading ? "Saving..." : "Save Configuration"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}

          {configs.length === 0 && !showForm && (
            <p className="text-sm text-muted-foreground">
              No email accounts configured yet.
            </p>
          )}

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
                      onClick={() => handleToggle(config)}
                    >
                      {config.is_enabled ? "Enabled" : "Disabled"}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleTest(config.id)}
                    >
                      Test
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive"
                      onClick={() => handleDelete(config.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* History table */}
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-foreground">
            Ingested Emails ({historyTotal})
          </h2>

          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No emails ingested yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="py-2 pr-4">Subject</th>
                    <th className="py-2 pr-4">Sender</th>
                    <th className="py-2 pr-4">Received</th>
                    <th className="py-2 pr-4">Attachments</th>
                    <th className="py-2 pr-4">Confidence</th>
                    <th className="py-2 pr-4">Status</th>
                    <th className="py-2 pr-4">Opportunity</th>
                    <th className="py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((item) => (
                    <tr
                      key={item.id}
                      className="border-b border-border last:border-0"
                    >
                      <td className="py-2 pr-4 max-w-[250px] truncate">
                        {item.subject}
                      </td>
                      <td className="py-2 pr-4">{item.sender}</td>
                      <td className="py-2 pr-4 whitespace-nowrap">
                        {new Date(item.received_at).toLocaleDateString()}
                      </td>
                      <td className="py-2 pr-4">
                        {item.attachment_count > 0
                          ? `${item.attachment_count} (${item.attachment_names.slice(0, 2).join(", ")})`
                          : "0"}
                      </td>
                      <td className="py-2 pr-4">
                        {item.classification_confidence !== null
                          ? item.classification_confidence.toFixed(2)
                          : "—"}
                      </td>
                      <td className="py-2 pr-4">
                        <Badge variant={statusVariant(item.processing_status)}>
                          {item.processing_status}
                        </Badge>
                      </td>
                      <td className="py-2 pr-4">
                        {item.created_rfp_id ? (
                          <a
                            className="text-primary underline"
                            href={`/opportunities/${item.created_rfp_id}`}
                          >
                            #{item.created_rfp_id}
                          </a>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="py-2">
                        {(item.processing_status === "error" ||
                          item.processing_status === "ignored") && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleReprocess(item.id)}
                          >
                            Reprocess
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
