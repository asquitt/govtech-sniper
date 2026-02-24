"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
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
import { IntegrationForm } from "./_components/IntegrationForm";
import { IntegrationsList } from "./_components/IntegrationsList";
import { AuditObservabilityCard } from "./_components/AuditObservabilityCard";
import { TeamRolesCard } from "./_components/TeamRolesCard";

const fallbackProviderOptions: { value: IntegrationProvider; label: string }[] = [
  { value: "okta", label: "Okta" },
  { value: "microsoft", label: "Microsoft" },
  { value: "sharepoint", label: "SharePoint" },
  { value: "salesforce", label: "Salesforce" },
  { value: "unanet", label: "Unanet" },
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
    setFieldValues((prev) => ({ ...prev, [key]: value }));
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

        <IntegrationForm
          provider={provider}
          providerOptions={providerOptions}
          selectedDefinition={selectedDefinition}
          name={name}
          fieldValues={fieldValues}
          onProviderChange={setProvider}
          onNameChange={setName}
          onFieldChange={handleFieldChange}
          onCreate={handleCreate}
        />

        <IntegrationsList
          integrations={integrations}
          getDefinitionForIntegration={getDefinitionForIntegration}
          testResults={testResults}
          syncRuns={syncRuns}
          webhookEvents={webhookEvents}
          ssoLinks={ssoLinks}
          onToggle={handleToggleIntegration}
          onTest={handleTest}
          onSync={handleSync}
          onAuthorizeSso={handleAuthorizeSso}
          onLoadSyncs={handleLoadSyncs}
          onSendWebhook={handleSendWebhook}
          onLoadWebhooks={handleLoadWebhooks}
        />

        <AuditObservabilityCard
          auditSummary={auditSummary}
          auditEvents={auditEvents}
          observability={observability}
        />

        <TeamRolesCard
          teams={teams}
          selectedTeamId={selectedTeamId}
          teamMembers={teamMembers}
          roleEdits={roleEdits}
          isLoadingTeams={isLoadingTeams}
          roleOptions={roleOptions}
          onTeamChange={setSelectedTeamId}
          onRoleEdit={(userId, role) =>
            setRoleEdits((prev) => ({ ...prev, [userId]: role }))
          }
          onUpdateRole={handleUpdateRole}
        />
      </div>
    </div>
  );
}
