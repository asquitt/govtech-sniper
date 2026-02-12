"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Cloud, KeyRound, Link2, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SharePointBrowser } from "@/components/integrations/sharepoint-browser";
import { enterpriseApi } from "@/lib/api";
import type {
  SecretItem,
  SharePointFile,
  WebhookDelivery,
  WebhookSubscription,
} from "@/types";

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString();
}

export default function IntegrationsPage() {
  const [webhooks, setWebhooks] = useState<WebhookSubscription[]>([]);
  const [secrets, setSecrets] = useState<SecretItem[]>([]);
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

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextWebhooks, nextSecrets] = await Promise.all([
        enterpriseApi.listWebhooks(),
        enterpriseApi.listSecrets(),
      ]);
      setWebhooks(nextWebhooks);
      setSecrets(nextSecrets);
    } catch (err) {
      console.error("Failed to load enterprise controls", err);
      setError("Failed to load enterprise integration controls.");
    } finally {
      setLoading(false);
    }
  }, []);

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
