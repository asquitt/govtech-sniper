"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type {
  IntegrationConfig,
  IntegrationProvider,
  IntegrationProviderDefinition,
  IntegrationSsoAuthorizeResponse,
  IntegrationSyncRun,
  IntegrationTestResult,
  IntegrationWebhookEvent,
} from "@/types";

interface IntegrationsListProps {
  integrations: IntegrationConfig[];
  getDefinitionForIntegration: (provider: IntegrationProvider) => IntegrationProviderDefinition | undefined;
  testResults: Record<number, IntegrationTestResult | null>;
  syncRuns: Record<number, IntegrationSyncRun[]>;
  webhookEvents: Record<number, IntegrationWebhookEvent[]>;
  ssoLinks: Record<number, IntegrationSsoAuthorizeResponse | null>;
  onToggle: (integration: IntegrationConfig) => void;
  onTest: (integrationId: number) => void;
  onSync: (integrationId: number) => void;
  onAuthorizeSso: (integrationId: number) => void;
  onLoadSyncs: (integrationId: number) => void;
  onSendWebhook: (integrationId: number) => void;
  onLoadWebhooks: (integrationId: number) => void;
}

export function IntegrationsList({
  integrations,
  getDefinitionForIntegration,
  testResults,
  syncRuns,
  webhookEvents,
  ssoLinks,
  onToggle,
  onTest,
  onSync,
  onAuthorizeSso,
  onLoadSyncs,
  onSendWebhook,
  onLoadWebhooks,
}: IntegrationsListProps) {
  return (
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
                        onClick={() => onToggle(integration)}
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
                    <Button size="sm" variant="outline" onClick={() => onTest(integration.id)}>
                      Test
                    </Button>
                    {definition?.category === "sso" && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onAuthorizeSso(integration.id)}
                      >
                        Generate SSO URL
                      </Button>
                    )}
                    {definition?.supports_sync && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onSync(integration.id)}
                        >
                          Run Sync
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onLoadSyncs(integration.id)}
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
                          onClick={() => onSendWebhook(integration.id)}
                        >
                          Send Test Webhook
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onLoadWebhooks(integration.id)}
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
  );
}
