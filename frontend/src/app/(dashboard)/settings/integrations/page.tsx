"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Cloud,
  Database,
  KeyRound,
  Link2,
  RefreshCw,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SharePointBrowser } from "@/components/integrations/sharepoint-browser";
import { enterpriseApi, unanetApi } from "@/lib/api";
import type {
  SecretItem,
  SharePointFile,
  UnanetFinancialRecord,
  UnanetResource,
  UnanetStatus,
  WebhookDelivery,
  WebhookSubscription,
} from "@/types";

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString();
}

export default function IntegrationsPage() {
  const [webhooks, setWebhooks] = useState<WebhookSubscription[]>([]);
  const [secrets, setSecrets] = useState<SecretItem[]>([]);
  const [unanetStatus, setUnanetStatus] = useState<UnanetStatus | null>(null);
  const [unanetResources, setUnanetResources] = useState<UnanetResource[]>([]);
  const [unanetFinancials, setUnanetFinancials] = useState<UnanetFinancialRecord[]>(
    []
  );
  const [unanetSyncMessage, setUnanetSyncMessage] = useState<string | null>(null);
  const [syncingResources, setSyncingResources] = useState(false);
  const [syncingFinancials, setSyncingFinancials] = useState(false);
  const [refreshingUnanet, setRefreshingUnanet] = useState(false);
  const [selectedSharePointFile, setSelectedSharePointFile] = useState<SharePointFile | null>(null);
  const [deliveriesByWebhook, setDeliveriesByWebhook] = useState<
    Record<number, WebhookDelivery[]>
  >({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [webhookName, setWebhookName] = useState("");
  const [webhookTargetUrl, setWebhookTargetUrl] = useState("");
  const [webhookEventTypes, setWebhookEventTypes] = useState("rfp.created");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [webhookSecretEdits, setWebhookSecretEdits] = useState<Record<number, string>>({});

  const [secretKey, setSecretKey] = useState("");
  const [secretValue, setSecretValue] = useState("");
  const [secretValueEdits, setSecretValueEdits] = useState<Record<string, string>>({});

  const totalFundedValue = unanetFinancials.reduce(
    (sum, record) => sum + record.funded_value,
    0
  );

  const loadUnanetData = useCallback(async () => {
    const status = await unanetApi.getStatus();
    setUnanetStatus(status);
    if (!status.configured || !status.enabled) {
      setUnanetResources([]);
      setUnanetFinancials([]);
      return;
    }
    const [resources, financials] = await Promise.all([
      unanetApi.listResources(),
      unanetApi.listFinancials(),
    ]);
    setUnanetResources(resources);
    setUnanetFinancials(financials);
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [[nextWebhooks, nextSecrets]] = await Promise.all([
        Promise.all([enterpriseApi.listWebhooks(), enterpriseApi.listSecrets()]),
        loadUnanetData(),
      ]);
      setWebhooks(nextWebhooks);
      setSecrets(nextSecrets);
    } catch (err) {
      console.error("Failed to load enterprise controls", err);
      setError("Failed to load enterprise integration controls.");
    } finally {
      setLoading(false);
    }
  }, [loadUnanetData]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateWebhook = async () => {
    if (!webhookName.trim() || !webhookTargetUrl.trim()) {
      setError("Webhook name and target URL are required.");
      return;
    }

    try {
      const eventTypes = webhookEventTypes
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
      await enterpriseApi.createWebhook({
        name: webhookName.trim(),
        target_url: webhookTargetUrl.trim(),
        secret: webhookSecret.trim() || undefined,
        event_types: eventTypes,
        is_active: true,
      });
      setWebhookName("");
      setWebhookTargetUrl("");
      setWebhookSecret("");
      setWebhookEventTypes("rfp.created");
      await loadData();
    } catch (err) {
      console.error("Failed to create webhook", err);
      setError("Failed to create webhook.");
    }
  };

  const handleToggleWebhook = async (webhook: WebhookSubscription) => {
    try {
      await enterpriseApi.updateWebhook(webhook.id, {
        is_active: !webhook.is_active,
      });
      await loadData();
    } catch (err) {
      console.error("Failed to toggle webhook", err);
      setError("Failed to toggle webhook.");
    }
  };

  const handleRotateWebhookSecret = async (webhookId: number) => {
    const nextSecret = webhookSecretEdits[webhookId];
    if (!nextSecret?.trim()) {
      setError("Webhook secret cannot be empty when rotating.");
      return;
    }
    try {
      await enterpriseApi.updateWebhook(webhookId, { secret: nextSecret.trim() });
      setWebhookSecretEdits((previous) => ({ ...previous, [webhookId]: "" }));
      await loadData();
    } catch (err) {
      console.error("Failed to rotate webhook secret", err);
      setError("Failed to rotate webhook secret.");
    }
  };

  const handleLoadDeliveries = async (webhookId: number) => {
    try {
      const deliveries = await enterpriseApi.listWebhookDeliveries(webhookId);
      setDeliveriesByWebhook((previous) => ({ ...previous, [webhookId]: deliveries }));
    } catch (err) {
      console.error("Failed to load webhook deliveries", err);
      setError("Failed to load webhook deliveries.");
    }
  };

  const handleDeleteWebhook = async (webhookId: number) => {
    try {
      await enterpriseApi.deleteWebhook(webhookId);
      setDeliveriesByWebhook((previous) => {
        const next = { ...previous };
        delete next[webhookId];
        return next;
      });
      await loadData();
    } catch (err) {
      console.error("Failed to delete webhook", err);
      setError("Failed to delete webhook.");
    }
  };

  const handleStoreSecret = async () => {
    if (!secretKey.trim() || !secretValue.trim()) {
      setError("Secret key and value are required.");
      return;
    }
    try {
      await enterpriseApi.createOrUpdateSecret({
        key: secretKey.trim(),
        value: secretValue,
      });
      setSecretKey("");
      setSecretValue("");
      await loadData();
    } catch (err) {
      console.error("Failed to store secret", err);
      setError("Failed to store secret.");
    }
  };

  const handleRotateSecret = async (key: string) => {
    const nextValue = secretValueEdits[key];
    if (!nextValue?.trim()) {
      setError("Enter a replacement secret value.");
      return;
    }
    try {
      await enterpriseApi.createOrUpdateSecret({ key, value: nextValue });
      setSecretValueEdits((previous) => ({ ...previous, [key]: "" }));
      await loadData();
    } catch (err) {
      console.error("Failed to rotate secret", err);
      setError("Failed to rotate secret.");
    }
  };

  const handleDeleteSecret = async (key: string) => {
    try {
      await enterpriseApi.deleteSecret(key);
      await loadData();
    } catch (err) {
      console.error("Failed to delete secret", err);
      setError("Failed to delete secret.");
    }
  };

  const handleRefreshUnanet = async () => {
    setRefreshingUnanet(true);
    setUnanetSyncMessage(null);
    try {
      await loadUnanetData();
    } catch (err) {
      console.error("Failed to refresh Unanet data", err);
      setError("Failed to refresh Unanet data.");
    } finally {
      setRefreshingUnanet(false);
    }
  };

  const handleSyncResources = async () => {
    setSyncingResources(true);
    setUnanetSyncMessage(null);
    try {
      const result = await unanetApi.syncResources();
      setUnanetSyncMessage(
        `Resources sync ${result.status}: ${result.resources_synced} record(s) processed.`
      );
      await loadUnanetData();
    } catch (err) {
      console.error("Failed to sync Unanet resources", err);
      setError("Failed to sync Unanet resources.");
    } finally {
      setSyncingResources(false);
    }
  };

  const handleSyncFinancials = async () => {
    setSyncingFinancials(true);
    setUnanetSyncMessage(null);
    try {
      const result = await unanetApi.syncFinancials();
      setUnanetSyncMessage(
        `Financial sync ${result.status}: ${result.records_synced} record(s), total funded value $${result.total_funded_value.toLocaleString()}.`
      );
      await loadUnanetData();
    } catch (err) {
      console.error("Failed to sync Unanet financial records", err);
      setError("Failed to sync Unanet financial records.");
    } finally {
      setSyncingFinancials(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Cloud className="w-5 h-5 text-primary" />
        <div>
          <h1 className="text-xl font-bold">Integrations</h1>
          <p className="text-sm text-muted-foreground">
            Enterprise controls for webhook subscriptions and encrypted secrets.
          </p>
        </div>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {loading ? <p className="text-sm text-muted-foreground">Loading controls...</p> : null}

      <Card className="border border-border" data-testid="unanet-controls-card">
        <CardContent className="p-4 space-y-4">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-primary" />
            <p className="text-sm font-semibold">Unanet Resource + Financial Sync</p>
          </div>
          {unanetStatus?.configured ? (
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={unanetStatus.enabled ? "success" : "outline"}>
                {unanetStatus.enabled ? "Enabled" : "Disabled"}
              </Badge>
              <Badge
                variant={
                  unanetStatus.healthy === undefined || unanetStatus.healthy === null
                    ? "outline"
                    : unanetStatus.healthy
                    ? "success"
                    : "destructive"
                }
              >
                {unanetStatus.healthy === undefined || unanetStatus.healthy === null
                  ? "Health Unknown"
                  : unanetStatus.healthy
                  ? "Healthy"
                  : "Unhealthy"}
              </Badge>
              {unanetStatus.base_url ? <Badge variant="outline">{unanetStatus.base_url}</Badge> : null}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">
              Unanet integration is not configured yet. Add provider `unanet` in Settings to enable
              resource and financial sync.
            </p>
          )}

          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleRefreshUnanet}
              disabled={refreshingUnanet}
            >
              {refreshingUnanet ? "Refreshing..." : "Refresh Unanet Data"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleSyncResources}
              disabled={!unanetStatus?.configured || !unanetStatus.enabled || syncingResources}
            >
              {syncingResources ? "Syncing Resources..." : "Sync Resources"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleSyncFinancials}
              disabled={!unanetStatus?.configured || !unanetStatus.enabled || syncingFinancials}
            >
              {syncingFinancials ? "Syncing Financials..." : "Sync Financials"}
            </Button>
          </div>

          {unanetSyncMessage ? (
            <p className="text-xs text-muted-foreground">{unanetSyncMessage}</p>
          ) : null}

          {unanetStatus?.configured && unanetStatus.enabled ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <p className="text-xs font-medium text-foreground">
                  Resource Planning ({unanetResources.length})
                </p>
                {unanetResources.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No resource records available.</p>
                ) : (
                  <div className="rounded-md border border-border bg-background/40 p-2 space-y-1 text-xs">
                    {unanetResources.slice(0, 5).map((resource) => (
                      <div
                        key={resource.id}
                        className="flex items-center justify-between gap-2"
                      >
                        <span className="text-foreground truncate">
                          {resource.labor_category}
                        </span>
                        <span className="text-muted-foreground">
                          {resource.currency} {resource.hourly_rate.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <p className="text-xs font-medium text-foreground">
                  Financial Records ({unanetFinancials.length})
                </p>
                <p className="text-xs text-muted-foreground">
                  Total funded value: ${totalFundedValue.toLocaleString()}
                </p>
                {unanetFinancials.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No financial records available.</p>
                ) : (
                  <div className="rounded-md border border-border bg-background/40 p-2 space-y-1 text-xs">
                    {unanetFinancials.slice(0, 5).map((record) => (
                      <div
                        key={record.id}
                        className="flex items-center justify-between gap-2"
                      >
                        <span className="text-foreground truncate">{record.project_name}</span>
                        <span className="text-muted-foreground">
                          {record.currency} {record.funded_value.toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border border-border" data-testid="sharepoint-browser-card">
        <CardContent className="p-4 space-y-4">
          <div className="flex items-center gap-2">
            <Cloud className="w-4 h-4 text-primary" />
            <p className="text-sm font-semibold">SharePoint Browser</p>
          </div>
          <p className="text-xs text-muted-foreground">
            Browse configured SharePoint folders and select files for import workflows.
          </p>
          <SharePointBrowser onFileSelect={setSelectedSharePointFile} />
          {selectedSharePointFile ? (
            <div className="rounded-md border border-border bg-background/40 p-2 text-xs">
              Selected file:{" "}
              <span className="font-medium text-foreground">{selectedSharePointFile.name}</span>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border border-border" data-testid="webhook-controls-card">
        <CardContent className="p-4 space-y-4">
          <div className="flex items-center gap-2">
            <Link2 className="w-4 h-4 text-primary" />
            <p className="text-sm font-semibold">Webhook Subscriptions</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label className="text-xs text-muted-foreground">
              Webhook name
              <input
                aria-label="Webhook name"
                className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Procurement Events"
                value={webhookName}
                onChange={(event) => setWebhookName(event.target.value)}
              />
            </label>
            <label className="text-xs text-muted-foreground">
              Target URL
              <input
                aria-label="Webhook target URL"
                className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="https://example.com/hooks/rfp"
                value={webhookTargetUrl}
                onChange={(event) => setWebhookTargetUrl(event.target.value)}
              />
            </label>
            <label className="text-xs text-muted-foreground">
              Event types (comma separated)
              <input
                aria-label="Webhook event types"
                className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="rfp.created,proposal.section.updated"
                value={webhookEventTypes}
                onChange={(event) => setWebhookEventTypes(event.target.value)}
              />
            </label>
            <label className="text-xs text-muted-foreground">
              Signing secret (optional)
              <input
                aria-label="Webhook signing secret"
                className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="whsec_..."
                value={webhookSecret}
                onChange={(event) => setWebhookSecret(event.target.value)}
              />
            </label>
          </div>
          <Button onClick={handleCreateWebhook}>Create Webhook</Button>

          <div className="space-y-3">
            {webhooks.length === 0 ? (
              <p className="text-sm text-muted-foreground">No webhook subscriptions configured.</p>
            ) : (
              webhooks.map((webhook) => (
                <div
                  key={webhook.id}
                  className="rounded-md border border-border px-3 py-3 space-y-2"
                  data-testid={`webhook-row-${webhook.id}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-foreground">{webhook.name}</p>
                      <p className="text-xs text-muted-foreground">{webhook.target_url}</p>
                    </div>
                    <Badge variant={webhook.is_active ? "success" : "outline"}>
                      {webhook.is_active ? "Active" : "Disabled"}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Events: {webhook.event_types.join(", ") || "None"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Updated: {formatTimestamp(webhook.updated_at)}
                  </p>

                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" onClick={() => handleToggleWebhook(webhook)}>
                      <ShieldCheck className="w-3.5 h-3.5" />
                      {webhook.is_active ? "Disable" : "Enable"}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleLoadDeliveries(webhook.id)}>
                      <RefreshCw className="w-3.5 h-3.5" />
                      Load Deliveries
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleDeleteWebhook(webhook.id)}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Delete
                    </Button>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      aria-label={`Rotate secret for ${webhook.name}`}
                      className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
                      placeholder="New signing secret"
                      value={webhookSecretEdits[webhook.id] || ""}
                      onChange={(event) =>
                        setWebhookSecretEdits((previous) => ({
                          ...previous,
                          [webhook.id]: event.target.value,
                        }))
                      }
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleRotateWebhookSecret(webhook.id)}
                    >
                      Rotate Secret
                    </Button>
                  </div>

                  {deliveriesByWebhook[webhook.id] ? (
                    <div className="rounded-md border border-border bg-background/40 p-2 space-y-1 text-xs">
                      {deliveriesByWebhook[webhook.id].length === 0 ? (
                        <p className="text-muted-foreground">No deliveries recorded.</p>
                      ) : (
                        deliveriesByWebhook[webhook.id].slice(0, 5).map((delivery) => (
                          <div
                            key={delivery.id}
                            className="flex items-center justify-between gap-2"
                          >
                            <span className="text-foreground">{delivery.event_type}</span>
                            <span className="text-muted-foreground">
                              {delivery.status} · {formatTimestamp(delivery.created_at)}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="border border-border" data-testid="secrets-controls-card">
        <CardContent className="p-4 space-y-4">
          <div className="flex items-center gap-2">
            <KeyRound className="w-4 h-4 text-primary" />
            <p className="text-sm font-semibold">Secrets Vault</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label className="text-xs text-muted-foreground">
              Secret key
              <input
                aria-label="Secret key"
                className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="SCIM_BEARER_TOKEN"
                value={secretKey}
                onChange={(event) => setSecretKey(event.target.value)}
              />
            </label>
            <label className="text-xs text-muted-foreground">
              Secret value
              <input
                aria-label="Secret value"
                className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="paste value"
                value={secretValue}
                onChange={(event) => setSecretValue(event.target.value)}
              />
            </label>
          </div>
          <Button onClick={handleStoreSecret}>Store Secret</Button>

          <div className="space-y-3">
            {secrets.length === 0 ? (
              <p className="text-sm text-muted-foreground">No secrets stored yet.</p>
            ) : (
              secrets.map((secret) => (
                <div
                  key={secret.id}
                  className="rounded-md border border-border px-3 py-3 space-y-2"
                  data-testid={`secret-row-${secret.key}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-foreground">{secret.key}</p>
                      <p className="text-xs text-muted-foreground">
                        Updated: {formatTimestamp(secret.updated_at)}
                      </p>
                    </div>
                    <Badge variant="outline">{secret.value}</Badge>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      aria-label={`Rotate value for ${secret.key}`}
                      className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
                      placeholder="New secret value"
                      value={secretValueEdits[secret.key] || ""}
                      onChange={(event) =>
                        setSecretValueEdits((previous) => ({
                          ...previous,
                          [secret.key]: event.target.value,
                        }))
                      }
                    />
                    <Button size="sm" variant="outline" onClick={() => handleRotateSecret(secret.key)}>
                      Rotate
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleDeleteSecret(secret.key)}>
                      <Trash2 className="w-3.5 h-3.5" />
                      Delete
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
