"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { integrationApi } from "@/lib/api";
import type { IntegrationConfig, IntegrationProvider } from "@/types";

const providerOptions: { value: IntegrationProvider; label: string }[] = [
  { value: "okta", label: "Okta" },
  { value: "microsoft", label: "Microsoft" },
  { value: "sharepoint", label: "SharePoint" },
  { value: "salesforce", label: "Salesforce" },
  { value: "word_addin", label: "Word Add-in" },
  { value: "webhook", label: "Webhook" },
  { value: "slack", label: "Slack" },
];

export default function SettingsPage() {
  const [integrations, setIntegrations] = useState<IntegrationConfig[]>([]);
  const [provider, setProvider] = useState<IntegrationProvider>("okta");
  const [name, setName] = useState("");
  const [config, setConfig] = useState("{}");
  const [error, setError] = useState<string | null>(null);

  const fetchIntegrations = useCallback(async () => {
    try {
      const list = await integrationApi.list();
      setIntegrations(list);
    } catch (err) {
      console.error("Failed to load integrations", err);
      setError("Failed to load integrations.");
    }
  }, []);

  useEffect(() => {
    fetchIntegrations();
  }, [fetchIntegrations]);

  const handleCreate = async () => {
    try {
      const parsed = config.trim() ? JSON.parse(config) : {};
      await integrationApi.create({
        provider,
        name: name.trim() || undefined,
        config: parsed,
      });
      setName("");
      setConfig("{}");
      await fetchIntegrations();
    } catch (err) {
      console.error("Failed to create integration", err);
      setError("Failed to create integration. Ensure JSON config is valid.");
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Settings"
        description="Manage integrations and admin configuration"
      />

      <div className="flex-1 p-6 overflow-auto space-y-6">
        {error && <p className="text-destructive">{error}</p>}

        <Card className="border border-border">
          <CardContent className="p-4 space-y-3">
            <p className="text-sm font-medium">Add Integration</p>
            <div className="grid grid-cols-3 gap-3">
              <select
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                value={provider}
                onChange={(e) => setProvider(e.target.value as IntegrationProvider)}
              >
                {providerOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <input
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Name (optional)"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <input
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder='Config JSON (e.g. {"domain":"example"})'
                value={config}
                onChange={(e) => setConfig(e.target.value)}
              />
            </div>
            <Button onClick={handleCreate}>Create Integration</Button>
          </CardContent>
        </Card>

        <Card className="border border-border">
          <CardContent className="p-4 space-y-3">
            <p className="text-sm font-medium">Integrations</p>
            {integrations.length === 0 ? (
              <p className="text-sm text-muted-foreground">No integrations yet.</p>
            ) : (
              <div className="space-y-2">
                {integrations.map((integration) => (
                  <div
                    key={integration.id}
                    className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                  >
                    <div>
                      <p className="font-medium text-foreground">
                        {integration.name || integration.provider}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Provider: {integration.provider}
                      </p>
                    </div>
                    <Badge variant={integration.is_enabled ? "success" : "outline"}>
                      {integration.is_enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
