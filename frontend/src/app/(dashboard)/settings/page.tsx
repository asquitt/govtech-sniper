"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { analyticsApi, auditApi, integrationApi, teamApi } from "@/lib/api";
import type {
  AuditEvent,
  AuditSummary,
  IntegrationConfig,
  IntegrationProvider,
  IntegrationProviderDefinition,
  IntegrationSsoAuthorizeResponse,
  IntegrationSyncRun,
  IntegrationTestResult,
  IntegrationWebhookEvent,
  ObservabilityMetrics,
} from "@/types";
import type { Team, TeamMember, TeamRole } from "@/lib/api";

const fallbackProviderOptions: { value: IntegrationProvider; label: string }[] = [
  { value: "okta", label: "Okta" },
  { value: "microsoft", label: "Microsoft" },
  { value: "sharepoint", label: "SharePoint" },
  { value: "salesforce", label: "Salesforce" },
  { value: "word_addin", label: "Word Add-in" },
  { value: "webhook", label: "Webhook" },
  { value: "slack", label: "Slack" },
];

const roleOptions: TeamRole[] = ["owner", "admin", "member", "viewer"];

export default function SettingsPage() {
  const [integrations, setIntegrations] = useState<IntegrationConfig[]>([]);
  const [providerDefinitions, setProviderDefinitions] =
    useState<IntegrationProviderDefinition[]>([]);
  const [provider, setProvider] = useState<IntegrationProvider>("okta");
  const [name, setName] = useState("");
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [roleEdits, setRoleEdits] = useState<Record<number, TeamRole>>({});
  const [isLoadingTeams, setIsLoadingTeams] = useState(false);
  const [testResults, setTestResults] = useState<
    Record<number, IntegrationTestResult | null>
  >({});
  const [syncRuns, setSyncRuns] = useState<
    Record<number, IntegrationSyncRun[]>
  >({});
  const [webhookEvents, setWebhookEvents] = useState<
    Record<number, IntegrationWebhookEvent[]>
  >({});
  const [ssoLinks, setSsoLinks] = useState<
    Record<number, IntegrationSsoAuthorizeResponse | null>
  >({});
  const [observability, setObservability] = useState<ObservabilityMetrics | null>(
    null
  );
  const [auditSummary, setAuditSummary] = useState<AuditSummary | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);

  const providerOptions = useMemo(() => {
    if (providerDefinitions.length === 0) {
      return fallbackProviderOptions;
    }
    return providerDefinitions.map((definition) => ({
      value: definition.provider,
      label: definition.label,
    }));
  }, [providerDefinitions]);

  const selectedDefinition = useMemo(
    () => providerDefinitions.find((definition) => definition.provider === provider),
    [providerDefinitions, provider]
  );

  const getDefinitionForIntegration = useCallback(
    (providerValue: IntegrationProvider) =>
      providerDefinitions.find((definition) => definition.provider === providerValue),
    [providerDefinitions]
  );

  const fetchIntegrations = useCallback(async () => {
    try {
      const list = await integrationApi.list();
      setIntegrations(list);
    } catch (err) {
      console.error("Failed to load integrations", err);
      setError("Failed to load integrations.");
    }
  }, []);

  const fetchProviders = useCallback(async () => {
    try {
      const list = await integrationApi.providers();
      setProviderDefinitions(list);
      if (list.length > 0) {
        setProvider((current) => current || list[0].provider);
      }
    } catch (err) {
      console.error("Failed to load provider definitions", err);
    }
  }, []);

  const fetchTeams = useCallback(async () => {
    try {
      setIsLoadingTeams(true);
      const list = await teamApi.list();
      setTeams(list);
      if (list.length > 0) {
        setSelectedTeamId((current) => current ?? list[0].id);
      }
    } catch (err) {
      console.error("Failed to load teams", err);
    } finally {
      setIsLoadingTeams(false);
    }
  }, []);

  const fetchObservability = useCallback(async () => {
    try {
      const metrics = await analyticsApi.getObservability({ days: 30 });
      setObservability(metrics);
    } catch (err) {
      console.error("Failed to load observability metrics", err);
    }
  }, []);

  const fetchAuditData = useCallback(async () => {
    try {
      const [summary, events] = await Promise.all([
        auditApi.summary({ days: 30 }),
        auditApi.list({ limit: 6 }),
      ]);
      setAuditSummary(summary);
      setAuditEvents(events);
    } catch (err) {
      console.error("Failed to load audit data", err);
    }
  }, []);

  useEffect(() => {
    fetchIntegrations();
    fetchProviders();
    fetchTeams();
    fetchObservability();
    fetchAuditData();
  }, [
    fetchIntegrations,
    fetchProviders,
    fetchTeams,
    fetchObservability,
    fetchAuditData,
  ]);

  useEffect(() => {
    const fetchMembers = async () => {
      if (!selectedTeamId) {
        setTeamMembers([]);
        return;
      }
      try {
        const team = await teamApi.get(selectedTeamId);
        setTeamMembers(team.members);
        const roleMap: Record<number, TeamRole> = {};
        team.members.forEach((member) => {
          roleMap[member.user_id] = member.role;
        });
        setRoleEdits(roleMap);
      } catch (err) {
        console.error("Failed to load team members", err);
      }
    };
    fetchMembers();
  }, [selectedTeamId]);

  useEffect(() => {
    setFieldValues({});
  }, [provider]);

  const handleFieldChange = (key: string, value: string) => {
    setFieldValues((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleCreate = async () => {
    try {
      const config = Object.entries(fieldValues).reduce<Record<string, string>>(
        (acc, [key, value]) => {
          if (value !== "") {
            acc[key] = value;
          }
          return acc;
        },
        {}
      );
      await integrationApi.create({
        provider,
        name: name.trim() || undefined,
        config,
      });
      setName("");
      setFieldValues({});
      await fetchIntegrations();
    } catch (err) {
      console.error("Failed to create integration", err);
      setError("Failed to create integration.");
    }
  };

  const handleToggleIntegration = async (integration: IntegrationConfig) => {
    try {
      await integrationApi.update(integration.id, {
        is_enabled: !integration.is_enabled,
      });
      await fetchIntegrations();
    } catch (err) {
      console.error("Failed to update integration", err);
      setError("Failed to update integration.");
    }
  };

  const handleTest = async (integrationId: number) => {
    try {
      const result = await integrationApi.test(integrationId);
      setTestResults((prev) => ({ ...prev, [integrationId]: result }));
    } catch (err) {
      console.error("Failed to test integration", err);
      setError("Failed to test integration.");
    }
  };

  const handleSync = async (integrationId: number) => {
    try {
      await integrationApi.sync(integrationId);
      const runs = await integrationApi.syncs(integrationId);
      setSyncRuns((prev) => ({ ...prev, [integrationId]: runs }));
    } catch (err) {
      console.error("Failed to sync integration", err);
      setError("Failed to sync integration.");
    }
  };

  const handleAuthorizeSso = async (integrationId: number) => {
    try {
      const result = await integrationApi.authorizeSso(integrationId);
      setSsoLinks((prev) => ({ ...prev, [integrationId]: result }));
    } catch (err) {
      console.error("Failed to authorize SSO", err);
      setError("Failed to generate SSO authorization URL.");
    }
  };

  const handleLoadSyncs = async (integrationId: number) => {
    try {
      const runs = await integrationApi.syncs(integrationId);
      setSyncRuns((prev) => ({ ...prev, [integrationId]: runs }));
    } catch (err) {
      console.error("Failed to load sync history", err);
    }
  };

  const handleSendWebhook = async (integrationId: number) => {
    try {
      await integrationApi.sendWebhook(integrationId, {
        event_type: "test.event",
        sent_at: new Date().toISOString(),
      });
      const events = await integrationApi.listWebhooks(integrationId);
      setWebhookEvents((prev) => ({ ...prev, [integrationId]: events }));
    } catch (err) {
      console.error("Failed to send webhook", err);
      setError("Failed to send webhook event.");
    }
  };

  const handleLoadWebhooks = async (integrationId: number) => {
    try {
      const events = await integrationApi.listWebhooks(integrationId);
      setWebhookEvents((prev) => ({ ...prev, [integrationId]: events }));
    } catch (err) {
      console.error("Failed to load webhook events", err);
    }
  };

  const handleUpdateRole = async (userId: number) => {
    if (!selectedTeamId) return;
    try {
      const role = roleEdits[userId];
      await teamApi.updateMemberRole(selectedTeamId, userId, role);
      const team = await teamApi.get(selectedTeamId);
      setTeamMembers(team.members);
    } catch (err) {
      console.error("Failed to update role", err);
      setError("Failed to update team role.");
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
          <CardContent className="p-4 space-y-4">
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
              <div className="rounded-md border border-border bg-background px-2 py-1 text-sm flex items-center text-muted-foreground">
                {selectedDefinition?.category || "Loading provider fields"}
              </div>
            </div>

            {selectedDefinition ? (
              <div className="space-y-3">
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">Required fields</p>
                  <div className="grid grid-cols-2 gap-3">
                    {selectedDefinition.required_fields.map((field) => (
                      <input
                        key={field.key}
                        className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                        placeholder={field.label}
                        type={field.secret ? "password" : "text"}
                        value={fieldValues[field.key] || ""}
                        onChange={(e) => handleFieldChange(field.key, e.target.value)}
                      />
                    ))}
                  </div>
                </div>
                {selectedDefinition.optional_fields.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs text-muted-foreground">Optional fields</p>
                    <div className="grid grid-cols-2 gap-3">
                      {selectedDefinition.optional_fields.map((field) => (
                        <input
                          key={field.key}
                          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                          placeholder={field.label}
                          type={field.secret ? "password" : "text"}
                          value={fieldValues[field.key] || ""}
                          onChange={(e) => handleFieldChange(field.key, e.target.value)}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                Provider definitions are loading.
              </p>
            )}

            <Button onClick={handleCreate}>Create Integration</Button>
          </CardContent>
        </Card>

        <Card className="border border-border">
          <CardContent className="p-4 space-y-3">
            <p className="text-sm font-medium">Integrations</p>
            {integrations.length === 0 ? (
              <p className="text-sm text-muted-foreground">No integrations yet.</p>
            ) : (
              <div className="space-y-3">
                {integrations.map((integration) => {
                  const definition = getDefinitionForIntegration(integration.provider);
                  const testResult = testResults[integration.id];
                  const syncHistory = syncRuns[integration.id] || [];
                  const webhookHistory = webhookEvents[integration.id] || [];
                  const ssoLink = ssoLinks[integration.id];
                  const latestSync = syncHistory[0];
                  const latestWebhook = webhookHistory[0];

                  return (
                    <div
                      key={integration.id}
                      className="rounded-md border border-border px-3 py-3 space-y-2 text-sm"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-foreground">
                            {integration.name || integration.provider}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Provider: {definition?.label || integration.provider}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge
                            variant={integration.is_enabled ? "success" : "outline"}
                          >
                            {integration.is_enabled ? "Enabled" : "Disabled"}
                          </Badge>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleToggleIntegration(integration)}
                          >
                            Toggle
                          </Button>
                        </div>
                      </div>

                      {testResult && (
                        <div className="text-xs text-muted-foreground">
                          Test: {testResult.status} - {testResult.message}
                          {testResult.missing_fields.length > 0 && (
                            <span>
                              {" "}Missing: {testResult.missing_fields.join(", ")}
                            </span>
                          )}
                        </div>
                      )}

                      {latestSync && (
                        <div className="text-xs text-muted-foreground">
                          Last Sync: {latestSync.status} · {latestSync.items_synced} items
                        </div>
                      )}

                      {latestWebhook && (
                        <div className="text-xs text-muted-foreground">
                          Last Webhook: {latestWebhook.event_type}
                        </div>
                      )}

                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" variant="outline" onClick={() => handleTest(integration.id)}>
                          Test
                        </Button>
                        {definition?.category === "sso" && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleAuthorizeSso(integration.id)}
                          >
                            Generate SSO URL
                          </Button>
                        )}
                        {definition?.supports_sync && (
                          <>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleSync(integration.id)}
                            >
                              Run Sync
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleLoadSyncs(integration.id)}
                            >
                              Load Syncs
                            </Button>
                          </>
                        )}
                        {definition?.supports_webhooks && (
                          <>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleSendWebhook(integration.id)}
                            >
                              Send Test Webhook
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleLoadWebhooks(integration.id)}
                            >
                              Load Webhooks
                            </Button>
                          </>
                        )}
                      </div>

                      {definition?.supports_webhooks && (
                        <p className="text-xs text-muted-foreground">
                          Webhook endpoint: /api/v1/integrations/{integration.id}/webhook
                        </p>
                      )}

                      {definition?.category === "sso" && ssoLink && (
                        <p className="text-xs text-muted-foreground break-all">
                          SSO URL: {ssoLink.authorization_url}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border border-border">
          <CardContent className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Audit & Observability</p>
                <p className="text-xs text-muted-foreground">
                  Operational health and compliance reporting
                </p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 text-sm">
              <div className="rounded-md border border-border px-3 py-2">
                <p className="text-xs text-muted-foreground">Audit Events (30d)</p>
                <p className="text-lg font-semibold">
                  {auditSummary?.total_events ?? "--"}
                </p>
              </div>
              <div className="rounded-md border border-border px-3 py-2">
                <p className="text-xs text-muted-foreground">Sync Successes (30d)</p>
                <p className="text-lg font-semibold">
                  {observability?.integration_syncs.success ?? "--"}
                </p>
              </div>
              <div className="rounded-md border border-border px-3 py-2">
                <p className="text-xs text-muted-foreground">Webhook Events (30d)</p>
                <p className="text-lg font-semibold">
                  {observability?.webhook_events.total ?? "--"}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">Recent audit activity</p>
              {auditEvents.length === 0 ? (
                <p className="text-sm text-muted-foreground">No audit events yet.</p>
              ) : (
                <div className="space-y-2">
                  {auditEvents.map((event) => (
                    <div
                      key={event.id}
                      className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                    >
                      <div>
                        <p className="font-medium text-foreground">{event.action}</p>
                        <p className="text-xs text-muted-foreground">
                          {event.entity_type} · {new Date(event.created_at).toLocaleString()}
                        </p>
                      </div>
                      <Badge variant="outline">{event.entity_type}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border border-border">
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Team Roles</p>
                <p className="text-xs text-muted-foreground">
                  Manage access levels for your team
                </p>
              </div>
              {isLoadingTeams && (
                <span className="text-xs text-muted-foreground">Loading...</span>
              )}
            </div>

            {teams.length === 0 ? (
              <p className="text-sm text-muted-foreground">No teams found.</p>
            ) : (
              <div className="space-y-3">
                <select
                  className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                  value={selectedTeamId ?? ""}
                  onChange={(e) =>
                    setSelectedTeamId(
                      e.target.value ? Number(e.target.value) : null
                    )
                  }
                >
                  {teams.map((team) => (
                    <option key={team.id} value={team.id}>
                      {team.name}
                    </option>
                  ))}
                </select>

                <div className="space-y-2">
                  {teamMembers.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No members found.
                    </p>
                  ) : (
                    teamMembers.map((member) => (
                      <div
                        key={member.user_id}
                        className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                      >
                        <div>
                          <p className="font-medium text-foreground">
                            {member.full_name || member.email}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {member.email}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <select
                            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                            value={roleEdits[member.user_id] || member.role}
                            onChange={(e) =>
                              setRoleEdits((prev) => ({
                                ...prev,
                                [member.user_id]: e.target.value as TeamRole,
                              }))
                            }
                          >
                            {roleOptions.map((role) => (
                              <option key={role} value={role}>
                                {role}
                              </option>
                            ))}
                          </select>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleUpdateRole(member.user_id)}
                          >
                            Update
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
