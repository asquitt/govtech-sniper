"use client";

import Link from "next/link";
import React, { useEffect, useState, useCallback, useRef } from "react";
import {
  Users,
  Mail,
  Eye,
  Edit3,
  Shield,
  Copy,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { collaborationApi } from "@/lib/api";
import { getApiErrorMessage, isStepUpRequiredError } from "@/lib/api/error";
import { StepUpAuthModal } from "@/components/security/step-up-auth-modal";
import type {
  ComplianceDigestDeliveryList,
  ComplianceDigestPreview,
  ComplianceDigestSchedule,
  ContractFeedCatalogItem,
  ContractFeedPresetItem,
  GovernanceAnomaly,
  ShareGovernanceSummary,
  ShareGovernanceTrends,
  SharedWorkspace,
  WorkspaceInvitation,
  WorkspaceMember,
  SharedDataPermission,
} from "@/types";
import { GovernanceSnapshot } from "./governance-snapshot";
import { ComplianceDigestPanel } from "./compliance-digest-panel";
import { ShareDataForm } from "./share-data-form";
import { SharedDataList } from "./shared-data-list";

// ---------------------------------------------------------------------------
// Invite Form (internal to workspace detail)
// ---------------------------------------------------------------------------

function InviteForm({
  workspaceId,
  onInvited,
}: {
  workspaceId: number;
  onInvited: () => void;
}) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("viewer");
  const [loading, setLoading] = useState(false);

  const handleInvite = async () => {
    if (!email.trim()) return;
    setLoading(true);
    try {
      await collaborationApi.invite(workspaceId, { email: email.trim(), role });
      setEmail("");
      onInvited();
    } catch {
      /* handled by API interceptor */
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex gap-2 items-end">
      <div className="flex-1">
        <label className="text-xs text-muted-foreground mb-1 block">
          Email
        </label>
        <input
          className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          placeholder="partner@company.com"
          value={email}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground mb-1 block">Role</label>
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={role}
          onChange={(e) => setRole(e.target.value)}
        >
          <option value="viewer">Viewer</option>
          <option value="contributor">Contributor</option>
          <option value="admin">Admin</option>
        </select>
      </div>
      <Button size="sm" onClick={handleInvite} disabled={loading || !email.trim()}>
        <Mail className="w-3 h-3 mr-1" /> Invite
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Workspace Detail
// ---------------------------------------------------------------------------

interface WorkspaceDetailProps {
  workspace: SharedWorkspace;
  onRefresh: () => void;
}

export function WorkspaceDetail({
  workspace,
  onRefresh,
}: WorkspaceDetailProps) {
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [invitations, setInvitations] = useState<WorkspaceInvitation[]>([]);
  const [sharedData, setSharedData] = useState<SharedDataPermission[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"members" | "invitations" | "data">("members");
  const [copiedInvitationId, setCopiedInvitationId] = useState<number | null>(null);
  const [shareDataType, setShareDataType] =
    useState<SharedDataPermission["data_type"]>("rfp_summary");
  const [shareEntityId, setShareEntityId] = useState("");
  const [contractFeedCatalog, setContractFeedCatalog] = useState<ContractFeedCatalogItem[]>([]);
  const [contractFeedPresets, setContractFeedPresets] = useState<ContractFeedPresetItem[]>([]);
  const [governanceSummary, setGovernanceSummary] = useState<ShareGovernanceSummary | null>(null);
  const [governanceTrends, setGovernanceTrends] = useState<ShareGovernanceTrends | null>(null);
  const [governanceAnomalies, setGovernanceAnomalies] = useState<GovernanceAnomaly[]>([]);
  const [digestSchedule, setDigestSchedule] = useState<ComplianceDigestSchedule | null>(null);
  const [digestPreview, setDigestPreview] = useState<ComplianceDigestPreview | null>(null);
  const [digestDeliveries, setDigestDeliveries] =
    useState<ComplianceDigestDeliveryList | null>(null);
  const [selectedContractFeedId, setSelectedContractFeedId] = useState("");
  const [selectedPresetKey, setSelectedPresetKey] = useState("");
  const [selectedPartnerUserId, setSelectedPartnerUserId] = useState("");
  const [expirationDays, setExpirationDays] = useState("");
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [isSharing, setIsSharing] = useState(false);
  const [isApplyingPreset, setIsApplyingPreset] = useState(false);
  const [isExportingAudit, setIsExportingAudit] = useState(false);
  const [isSavingDigest, setIsSavingDigest] = useState(false);
  const [isSendingDigest, setIsSendingDigest] = useState(false);
  const [isStepUpModalOpen, setIsStepUpModalOpen] = useState(false);
  const [isStepUpSubmitting, setIsStepUpSubmitting] = useState(false);
  const [stepUpError, setStepUpError] = useState<string | null>(null);
  const [stepUpTitle, setStepUpTitle] = useState("Step-Up Authentication Required");
  const [stepUpDescription, setStepUpDescription] = useState(
    "Enter your current 6-digit MFA code to continue."
  );
  const stepUpRetryActionRef = useRef<((code: string) => Promise<void>) | null>(null);

  void onRefresh;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [
        m, i, s, contractFeeds, presets,
        governance, trends, anomalies, schedule, preview, deliveryTelemetry,
      ] = await Promise.all([
        collaborationApi.listMembers(workspace.id),
        collaborationApi.listInvitations(workspace.id).catch(() => [] as WorkspaceInvitation[]),
        collaborationApi.listSharedData(workspace.id),
        collaborationApi.listContractFeedCatalog().catch(() => [] as ContractFeedCatalogItem[]),
        collaborationApi.listContractFeedPresets().catch(() => [] as ContractFeedPresetItem[]),
        collaborationApi.getShareGovernanceSummary(workspace.id).catch(() => null as ShareGovernanceSummary | null),
        collaborationApi.getShareGovernanceTrends(workspace.id).catch(() => null as ShareGovernanceTrends | null),
        collaborationApi.getGovernanceAnomalies(workspace.id).catch(() => [] as GovernanceAnomaly[]),
        collaborationApi.getComplianceDigestSchedule(workspace.id).catch(() => null as ComplianceDigestSchedule | null),
        collaborationApi.getComplianceDigestPreview(workspace.id).catch(() => null as ComplianceDigestPreview | null),
        collaborationApi
          .getComplianceDigestDeliveries(workspace.id, { limit: 10 })
          .catch(() => null as ComplianceDigestDeliveryList | null),
      ]);
      setMembers(m);
      setInvitations(i);
      setSharedData(s);
      setContractFeedCatalog(contractFeeds);
      setContractFeedPresets(presets);
      setGovernanceSummary(governance);
      setGovernanceTrends(trends);
      setGovernanceAnomalies(anomalies);
      setDigestSchedule(schedule);
      setDigestPreview(preview);
      setDigestDeliveries(deliveryTelemetry);
      if (contractFeeds.length > 0 && !selectedContractFeedId) {
        setSelectedContractFeedId(String(contractFeeds[0].id));
      }
      if (presets.length > 0 && !selectedPresetKey) {
        setSelectedPresetKey(presets[0].key);
      }
    } catch {
      /* handled */
    } finally {
      setLoading(false);
    }
  }, [workspace.id, selectedContractFeedId, selectedPresetKey]);

  useEffect(() => {
    load();
  }, [load]);

  const roleIcon = (role: string) => {
    switch (role) {
      case "admin":
        return <Shield className="w-3 h-3" />;
      case "contributor":
        return <Edit3 className="w-3 h-3" />;
      default:
        return <Eye className="w-3 h-3" />;
    }
  };

  const tabs = [
    { key: "members" as const, label: "Members", count: members.length },
    { key: "invitations" as const, label: "Invitations", count: invitations.length },
    { key: "data" as const, label: "Shared Data", count: sharedData.length },
  ];

  const closeStepUpModal = useCallback(() => {
    setIsStepUpModalOpen(false);
    setStepUpError(null);
    stepUpRetryActionRef.current = null;
  }, []);

  const requestStepUpChallenge = useCallback(
    (
      retryAction: (code: string) => Promise<void>,
      options?: {
        title?: string;
        description?: string;
      }
    ) => {
      stepUpRetryActionRef.current = retryAction;
      setStepUpTitle(options?.title ?? "Step-Up Authentication Required");
      setStepUpDescription(
        options?.description ?? "Enter your current 6-digit MFA code to continue."
      );
      setStepUpError(null);
      setIsStepUpModalOpen(true);
    },
    []
  );

  const handleStepUpSubmit = useCallback(
    async (code: string) => {
      const retryAction = stepUpRetryActionRef.current;
      if (!retryAction) {
        closeStepUpModal();
        return;
      }
      setIsStepUpSubmitting(true);
      setStepUpError(null);
      try {
        await retryAction(code.trim());
        closeStepUpModal();
      } catch (error) {
        if (isStepUpRequiredError(error)) {
          setStepUpError("Invalid MFA code. Please try again.");
          return;
        }
        setStepUpError(getApiErrorMessage(error, "Unable to verify MFA code."));
      } finally {
        setIsStepUpSubmitting(false);
      }
    },
    [closeStepUpModal]
  );

  const downloadAuditCsv = useCallback(
    async (stepUpCode?: string) => {
      const blob = await collaborationApi.exportShareAuditCsv(workspace.id, {
        days: governanceTrends?.days ?? 30,
        step_up_code: stepUpCode || undefined,
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `workspace_${workspace.id}_share_audit.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
    [workspace.id, governanceTrends?.days]
  );

  const handleExportAudit = async () => {
    setIsExportingAudit(true);
    try {
      await downloadAuditCsv();
    } catch (error) {
      if (isStepUpRequiredError(error)) {
        requestStepUpChallenge(
          async (code) => {
            await downloadAuditCsv(code);
          },
          {
            title: "Step-Up Required for Audit Export",
            description:
              "Enter your current 6-digit MFA code to export collaboration audit evidence.",
          }
        );
        return;
      }
      /* handled by interceptor */
    } finally {
      setIsExportingAudit(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="h-8 w-48 rounded bg-muted animate-pulse" />
        <div className="h-32 w-full rounded bg-muted animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <StepUpAuthModal
        open={isStepUpModalOpen}
        title={stepUpTitle}
        description={stepUpDescription}
        isSubmitting={isStepUpSubmitting}
        error={stepUpError}
        onClose={closeStepUpModal}
        onSubmit={handleStepUpSubmit}
      />

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-foreground">{workspace.name}</h2>
          {workspace.description && (
            <p className="text-sm text-muted-foreground">{workspace.description}</p>
          )}
        </div>
        <Button asChild size="sm" variant="outline">
          <Link href={`/collaboration/portal/${workspace.id}`}>
            <ExternalLink className="w-3.5 h-3.5" />
            Open Partner Portal
          </Link>
        </Button>
      </div>

      {/* Invite */}
      <div className="p-3 rounded-lg border border-border bg-card">
        <h4 className="text-sm font-medium text-foreground mb-2">Invite Partner</h4>
        <InviteForm workspaceId={workspace.id} onInvited={load} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      {/* Members Tab */}
      {activeTab === "members" && (
        <div className="space-y-2">
          {members.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No members yet. Invite partners to collaborate.
            </p>
          )}
          {members.map((m) => (
            <div
              key={m.id}
              className="flex items-center justify-between p-3 rounded-lg border border-border"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                  <Users className="w-4 h-4 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {m.user_name || m.user_email || `User #${m.user_id}`}
                  </p>
                  {m.user_email && (
                    <p className="text-xs text-muted-foreground">{m.user_email}</p>
                  )}
                </div>
              </div>
              <Badge variant="outline" className="gap-1">
                {roleIcon(m.role)} {m.role}
              </Badge>
            </div>
          ))}
        </div>
      )}

      {/* Invitations Tab */}
      {activeTab === "invitations" && (
        <div className="space-y-2">
          {invitations.length === 0 && (
            <p className="text-sm text-muted-foreground">No pending invitations.</p>
          )}
          {invitations.map((inv) => (
            <div key={inv.id} className="p-3 rounded-lg border border-border" data-testid={`invitation-row-${inv.id}`}>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-foreground">{inv.email}</p>
                  <p className="text-xs text-muted-foreground">
                    Role: {inv.role} &middot; Expires:{" "}
                    {new Date(inv.expires_at).toLocaleDateString()}
                  </p>
                </div>
                <Badge variant={inv.is_accepted ? "default" : "secondary"}>
                  {inv.is_accepted ? "Accepted" : "Pending"}
                </Badge>
              </div>

              {inv.accept_token && (
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button asChild size="sm" variant="outline">
                    <Link href={`/collaboration/accept?token=${encodeURIComponent(inv.accept_token)}`}>
                      Accept Link
                    </Link>
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={async () => {
                      const link = `${window.location.origin}/collaboration/accept?token=${encodeURIComponent(inv.accept_token ?? "")}`;
                      try {
                        await navigator.clipboard.writeText(link);
                        setCopiedInvitationId(inv.id);
                        setTimeout(() => setCopiedInvitationId(null), 1500);
                      } catch {
                        /* noop */
                      }
                    }}
                  >
                    <Copy className="w-3.5 h-3.5" />
                    {copiedInvitationId === inv.id ? "Copied" : "Copy Link"}
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Shared Data Tab */}
      {activeTab === "data" && (
        <div className="space-y-2">
          <GovernanceSnapshot
            workspaceId={workspace.id}
            governanceSummary={governanceSummary}
            governanceTrends={governanceTrends}
            governanceAnomalies={governanceAnomalies}
            isExportingAudit={isExportingAudit}
            onExportAudit={handleExportAudit}
          />

          <ComplianceDigestPanel
            workspaceId={workspace.id}
            digestSchedule={digestSchedule}
            digestPreview={digestPreview}
            digestDeliveries={digestDeliveries}
            governanceTrends={governanceTrends}
            isSavingDigest={isSavingDigest}
            isSendingDigest={isSendingDigest}
            onDigestScheduleChange={setDigestSchedule}
            onDigestPreviewChange={setDigestPreview}
            onDigestDeliveriesChange={setDigestDeliveries}
            onSavingDigestChange={setIsSavingDigest}
            onSendingDigestChange={setIsSendingDigest}
          />

          <ShareDataForm
            workspaceId={workspace.id}
            members={members}
            shareDataType={shareDataType}
            shareEntityId={shareEntityId}
            contractFeedCatalog={contractFeedCatalog}
            contractFeedPresets={contractFeedPresets}
            selectedContractFeedId={selectedContractFeedId}
            selectedPresetKey={selectedPresetKey}
            selectedPartnerUserId={selectedPartnerUserId}
            expirationDays={expirationDays}
            requiresApproval={requiresApproval}
            isSharing={isSharing}
            isApplyingPreset={isApplyingPreset}
            onShareDataTypeChange={setShareDataType}
            onShareEntityIdChange={setShareEntityId}
            onSelectedContractFeedIdChange={setSelectedContractFeedId}
            onSelectedPresetKeyChange={setSelectedPresetKey}
            onSelectedPartnerUserIdChange={setSelectedPartnerUserId}
            onExpirationDaysChange={setExpirationDays}
            onRequiresApprovalChange={setRequiresApproval}
            onSharingChange={setIsSharing}
            onApplyingPresetChange={setIsApplyingPreset}
            onStepUpRequired={requestStepUpChallenge}
            onDataChanged={load}
          />

          <SharedDataList
            workspaceId={workspace.id}
            sharedData={sharedData}
            onDataChanged={load}
          />
        </div>
      )}
    </div>
  );
}
