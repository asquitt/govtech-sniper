"use client";

import Link from "next/link";
import React, { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Share2,
  Plus,
  Users,
  Mail,
  Eye,
  Edit3,
  Shield,
  Trash2,
  Activity,
  Copy,
  Download,
  ExternalLink,
} from "lucide-react";
import { collaborationApi } from "@/lib/api";
import type {
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
import { ActivityFeed } from "@/components/collaboration/activity-feed";

// ---------------------------------------------------------------------------
// Workspace List
// ---------------------------------------------------------------------------

function WorkspaceList({
  workspaces,
  selectedId,
  onSelect,
  onCreate,
}: {
  workspaces: SharedWorkspace[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onCreate: () => void;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-foreground">Workspaces</h3>
        <Button size="sm" variant="outline" onClick={onCreate}>
          <Plus className="w-3 h-3 mr-1" /> New
        </Button>
      </div>
      {workspaces.length === 0 && (
        <p className="text-sm text-muted-foreground">No workspaces yet.</p>
      )}
      {workspaces.map((ws) => (
        <button
          key={ws.id}
          onClick={() => onSelect(ws.id)}
          className={`w-full text-left p-3 rounded-lg border transition-colors ${
            selectedId === ws.id
              ? "border-primary bg-primary/10"
              : "border-border hover:bg-secondary"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-foreground truncate">
              {ws.name}
            </span>
            <Badge variant="secondary" className="text-[10px]">
              <Users className="w-3 h-3 mr-1" />
              {ws.member_count}
            </Badge>
          </div>
          {ws.description && (
            <p className="text-xs text-muted-foreground mt-1 truncate">
              {ws.description}
            </p>
          )}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Invite Form
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

function WorkspaceDetail({
  workspace,
  onRefresh,
}: {
  workspace: SharedWorkspace;
  onRefresh: () => void;
}) {
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

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [
        m,
        i,
        s,
        contractFeeds,
        presets,
        governance,
        trends,
        anomalies,
        schedule,
        preview,
      ] = await Promise.all([
        collaborationApi.listMembers(workspace.id),
        collaborationApi.listInvitations(workspace.id).catch(() => [] as WorkspaceInvitation[]),
        collaborationApi.listSharedData(workspace.id),
        collaborationApi.listContractFeedCatalog().catch(
          () => [] as ContractFeedCatalogItem[]
        ),
        collaborationApi.listContractFeedPresets().catch(
          () => [] as ContractFeedPresetItem[]
        ),
        collaborationApi.getShareGovernanceSummary(workspace.id).catch(
          () => null as ShareGovernanceSummary | null
        ),
        collaborationApi.getShareGovernanceTrends(workspace.id).catch(
          () => null as ShareGovernanceTrends | null
        ),
        collaborationApi.getGovernanceAnomalies(workspace.id).catch(
          () => [] as GovernanceAnomaly[]
        ),
        collaborationApi.getComplianceDigestSchedule(workspace.id).catch(
          () => null as ComplianceDigestSchedule | null
        ),
        collaborationApi.getComplianceDigestPreview(workspace.id).catch(
          () => null as ComplianceDigestPreview | null
        ),
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
  const scopedMemberOptions = Array.from(
    new Map(members.map((member) => [member.user_id, member])).values()
  );

  const formatExpiration = (expiresAt?: string | null) => {
    if (!expiresAt) return "No expiry";
    const expiryDate = new Date(expiresAt);
    if (Number.isNaN(expiryDate.getTime())) return "No expiry";
    return `Expires ${expiryDate.toLocaleDateString()}`;
  };
  const latestTrendPoints = (governanceTrends?.points ?? []).slice(-7).reverse();

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
          <div className="rounded-lg border border-border bg-card p-3">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium text-foreground">Governance Snapshot</p>
              <Button
                variant="outline"
                size="sm"
                data-testid="export-governance-audit"
                disabled={isExportingAudit}
                onClick={async () => {
                  setIsExportingAudit(true);
                  try {
                    const blob = await collaborationApi.exportShareAuditCsv(workspace.id, {
                      days: governanceTrends?.days ?? 30,
                    });
                    const url = window.URL.createObjectURL(blob);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = `workspace_${workspace.id}_share_audit.csv`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(url);
                  } catch {
                    /* handled by interceptor */
                  } finally {
                    setIsExportingAudit(false);
                  }
                }}
              >
                <Download className="w-3.5 h-3.5" />
                Export Audit CSV
              </Button>
            </div>
            {governanceSummary ? (
              <div className="space-y-2">
                <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2 lg:grid-cols-3">
                  <div className="rounded border border-border px-2 py-1">
                    Total shared:{" "}
                    <span data-testid="governance-total-count" className="font-semibold text-foreground">
                      {governanceSummary.total_shared_items}
                    </span>
                  </div>
                  <div className="rounded border border-border px-2 py-1">
                    Pending approvals:{" "}
                    <span
                      data-testid="governance-pending-count"
                      className="font-semibold text-foreground"
                    >
                      {governanceSummary.pending_approval_count}
                    </span>
                  </div>
                  <div className="rounded border border-border px-2 py-1">
                    Expiring in 7 days:{" "}
                    <span
                      data-testid="governance-expiring-count"
                      className="font-semibold text-foreground"
                    >
                      {governanceSummary.expiring_7d_count}
                    </span>
                  </div>
                  <div className="rounded border border-border px-2 py-1">
                    Expired:{" "}
                    <span
                      data-testid="governance-expired-count"
                      className="font-semibold text-foreground"
                    >
                      {governanceSummary.expired_count}
                    </span>
                  </div>
                  <div className="rounded border border-border px-2 py-1">
                    Scoped shares:{" "}
                    <span
                      data-testid="governance-scoped-count"
                      className="font-semibold text-foreground"
                    >
                      {governanceSummary.scoped_share_count}
                    </span>
                  </div>
                  <div className="rounded border border-border px-2 py-1">
                    Approved shares:{" "}
                    <span className="font-semibold text-foreground">
                      {governanceSummary.approved_count}
                    </span>
                  </div>
                </div>

                <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
                  <div className="rounded border border-border px-2 py-1">
                    SLA approvals ({governanceTrends?.sla_hours ?? 24}h):{" "}
                    <span
                      data-testid="governance-sla-percent"
                      className="font-semibold text-foreground"
                    >
                      {governanceTrends ? `${governanceTrends.sla_approval_rate}%` : "N/A"}
                    </span>
                  </div>
                  <div className="rounded border border-border px-2 py-1">
                    Pending past SLA:{" "}
                    <span
                      data-testid="governance-overdue-pending-count"
                      className="font-semibold text-foreground"
                    >
                      {governanceTrends?.overdue_pending_count ?? "N/A"}
                    </span>
                  </div>
                </div>

                {latestTrendPoints.length > 0 && (
                  <div className="rounded border border-border p-2">
                    <p className="mb-1 text-xs font-medium text-foreground">
                      Last 7 days trend (new / approvals / SLA-within)
                    </p>
                    <div className="space-y-1 text-[11px] text-muted-foreground">
                      {latestTrendPoints.map((point) => (
                        <div
                          key={point.date}
                          className="flex items-center justify-between rounded border border-border/60 px-2 py-1"
                        >
                          <span>{point.date}</span>
                          <span>
                            {point.shared_count} / {point.approvals_completed_count} /{" "}
                            {point.approved_within_sla_count}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                Governance metrics unavailable for this workspace.
              </p>
            )}
          </div>

          <div className="rounded-lg border border-border bg-card p-3">
            <p className="mb-2 text-sm font-medium text-foreground">Governance Anomaly Alerts</p>
            <div className="space-y-2">
              {governanceAnomalies.length === 0 ? (
                <p className="text-xs text-muted-foreground">No anomaly alerts available.</p>
              ) : (
                governanceAnomalies.map((anomaly) => (
                  <div
                    key={anomaly.code}
                    className="rounded border border-border px-2 py-1.5 text-xs"
                    data-testid={`governance-anomaly-${anomaly.code}`}
                  >
                    <p
                      className={`font-medium ${
                        anomaly.severity === "critical"
                          ? "text-destructive"
                          : anomaly.severity === "warning"
                            ? "text-yellow-600"
                            : "text-foreground"
                      }`}
                    >
                      {anomaly.title}
                    </p>
                    <p className="text-muted-foreground">{anomaly.description}</p>
                    <p className="text-muted-foreground">
                      Recommendation: {anomaly.recommendation}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="text-sm font-medium text-foreground">Compliance Digest</p>
              <Button
                size="sm"
                variant="outline"
                disabled={isSendingDigest || !digestSchedule?.is_enabled}
                onClick={async () => {
                  setIsSendingDigest(true);
                  try {
                    const preview = await collaborationApi.sendComplianceDigest(workspace.id, {
                      days: governanceTrends?.days ?? 30,
                      sla_hours: governanceTrends?.sla_hours ?? 24,
                    });
                    setDigestPreview(preview);
                    setDigestSchedule(preview.schedule);
                  } catch {
                    /* handled */
                  } finally {
                    setIsSendingDigest(false);
                  }
                }}
              >
                Send Now
              </Button>
            </div>
            {digestSchedule ? (
              <div className="space-y-2 text-xs">
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                  <label className="space-y-1 text-muted-foreground">
                    Frequency
                    <select
                      className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                      aria-label="Digest frequency"
                      value={digestSchedule.frequency}
                      onChange={(event) =>
                        setDigestSchedule((prev) =>
                          prev
                            ? {
                                ...prev,
                                frequency: event.target.value as "daily" | "weekly",
                              }
                            : prev
                        )
                      }
                    >
                      <option value="daily">daily</option>
                      <option value="weekly">weekly</option>
                    </select>
                  </label>
                  <label className="space-y-1 text-muted-foreground">
                    Day (weekly)
                    <input
                      aria-label="Digest day"
                      type="number"
                      min={0}
                      max={6}
                      className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                      value={digestSchedule.day_of_week ?? 1}
                      onChange={(event) =>
                        setDigestSchedule((prev) =>
                          prev
                            ? {
                                ...prev,
                                day_of_week:
                                  Number.parseInt(event.target.value, 10) || 0,
                              }
                            : prev
                        )
                      }
                    />
                  </label>
                  <label className="space-y-1 text-muted-foreground">
                    Hour UTC
                    <input
                      aria-label="Digest hour UTC"
                      type="number"
                      min={0}
                      max={23}
                      className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                      value={digestSchedule.hour_utc}
                      onChange={(event) =>
                        setDigestSchedule((prev) =>
                          prev
                            ? {
                                ...prev,
                                hour_utc:
                                  Number.parseInt(event.target.value, 10) || 0,
                              }
                            : prev
                        )
                      }
                    />
                  </label>
                  <label className="space-y-1 text-muted-foreground">
                    Minute UTC
                    <input
                      aria-label="Digest minute UTC"
                      type="number"
                      min={0}
                      max={59}
                      className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                      value={digestSchedule.minute_utc}
                      onChange={(event) =>
                        setDigestSchedule((prev) =>
                          prev
                            ? {
                                ...prev,
                                minute_utc:
                                  Number.parseInt(event.target.value, 10) || 0,
                              }
                            : prev
                        )
                      }
                    />
                  </label>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <label className="flex items-center gap-2 text-muted-foreground">
                    <input
                      type="checkbox"
                      aria-label="Digest anomalies only"
                      checked={digestSchedule.anomalies_only}
                      onChange={(event) =>
                        setDigestSchedule((prev) =>
                          prev
                            ? { ...prev, anomalies_only: event.target.checked }
                            : prev
                        )
                      }
                    />
                    anomalies only
                  </label>
                  <label className="flex items-center gap-2 text-muted-foreground">
                    <input
                      type="checkbox"
                      aria-label="Digest enabled"
                      checked={digestSchedule.is_enabled}
                      onChange={(event) =>
                        setDigestSchedule((prev) =>
                          prev ? { ...prev, is_enabled: event.target.checked } : prev
                        )
                      }
                    />
                    enabled
                  </label>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={isSavingDigest}
                    onClick={async () => {
                      if (!digestSchedule) return;
                      setIsSavingDigest(true);
                      try {
                        const updated = await collaborationApi.updateComplianceDigestSchedule(
                          workspace.id,
                          {
                            frequency: digestSchedule.frequency,
                            day_of_week: digestSchedule.day_of_week,
                            hour_utc: digestSchedule.hour_utc,
                            minute_utc: digestSchedule.minute_utc,
                            channel: digestSchedule.channel,
                            anomalies_only: digestSchedule.anomalies_only,
                            is_enabled: digestSchedule.is_enabled,
                          }
                        );
                        setDigestSchedule(updated);
                        const preview = await collaborationApi.getComplianceDigestPreview(
                          workspace.id
                        );
                        setDigestPreview(preview);
                      } catch {
                        /* handled */
                      } finally {
                        setIsSavingDigest(false);
                      }
                    }}
                  >
                    Save Schedule
                  </Button>
                </div>
                <p className="text-muted-foreground">
                  Last sent:{" "}
                  {digestSchedule.last_sent_at
                    ? new Date(digestSchedule.last_sent_at).toLocaleString()
                    : "never"}
                </p>
                {digestPreview ? (
                  <p className="text-muted-foreground" data-testid="compliance-digest-preview">
                    Preview anomalies: {digestPreview.anomalies.length} · pending approvals:{" "}
                    {digestPreview.summary.pending_approval_count}
                  </p>
                ) : (
                  <p className="text-muted-foreground">
                    Preview unavailable for this workspace.
                  </p>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                Digest schedule unavailable for this workspace.
              </p>
            )}
          </div>

          <div className="rounded-lg border border-border bg-card p-3">
            <p className="text-sm font-medium text-foreground mb-2">
              Apply Contract Feed Preset
            </p>
            <div className="flex flex-wrap items-end gap-2">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Preset</label>
                <select
                  className="h-9 min-w-64 rounded-md border border-input bg-background px-3 text-sm"
                  aria-label="Contract feed preset"
                  value={selectedPresetKey}
                  onChange={(e) => setSelectedPresetKey(e.target.value)}
                >
                  {contractFeedPresets.length === 0 && (
                    <option value="">No presets available</option>
                  )}
                  {contractFeedPresets.map((preset) => (
                    <option key={preset.key} value={preset.key}>
                      {preset.name}
                    </option>
                  ))}
                </select>
                {selectedPresetKey && (
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    {
                      contractFeedPresets.find((preset) => preset.key === selectedPresetKey)
                        ?.description
                    }
                  </p>
                )}
              </div>
              <Button
                size="sm"
                disabled={isApplyingPreset || !selectedPresetKey}
                onClick={async () => {
                  if (!selectedPresetKey) return;
                  setIsApplyingPreset(true);
                  try {
                    await collaborationApi.applyContractFeedPreset(
                      workspace.id,
                      selectedPresetKey
                    );
                    await load();
                  } catch {
                    /* handled by interceptor */
                  } finally {
                    setIsApplyingPreset(false);
                  }
                }}
              >
                Apply Preset
              </Button>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-3">
            <p className="text-sm font-medium text-foreground mb-2">Share New Data</p>
            <div className="flex flex-wrap items-end gap-2">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Type</label>
                <select
                  className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                  aria-label="Shared data type"
                  value={shareDataType}
                  onChange={(e) =>
                    setShareDataType(e.target.value as SharedDataPermission["data_type"])
                  }
                >
                  <option value="rfp_summary">RFP Summary</option>
                  <option value="compliance_matrix">Compliance Matrix</option>
                  <option value="proposal_section">Proposal Section</option>
                  <option value="forecast">Forecast</option>
                  <option value="contract_feed">Contract Feed</option>
                </select>
              </div>
              {shareDataType === "contract_feed" ? (
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">
                    Contract Feed
                  </label>
                  <select
                    className="h-9 min-w-56 rounded-md border border-input bg-background px-3 text-sm"
                    aria-label="Contract Feed"
                    value={selectedContractFeedId}
                    onChange={(e) => setSelectedContractFeedId(e.target.value)}
                  >
                    {contractFeedCatalog.length === 0 && (
                      <option value="">No feeds available</option>
                    )}
                    {contractFeedCatalog.map((feed) => (
                      <option key={feed.id} value={feed.id}>
                        {feed.name}
                      </option>
                    ))}
                  </select>
                  {selectedContractFeedId && (
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      {
                        contractFeedCatalog.find(
                          (feed) => String(feed.id) === selectedContractFeedId
                        )?.description
                      }
                    </p>
                  )}
                </div>
              ) : (
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Entity ID</label>
                  <input
                    type="number"
                    min={1}
                    aria-label="Shared entity id"
                    className="h-9 w-32 rounded-md border border-input bg-background px-3 text-sm"
                    value={shareEntityId}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setShareEntityId(e.target.value)}
                    placeholder="123"
                  />
                </div>
              )}
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Visible To</label>
                <select
                  className="h-9 min-w-48 rounded-md border border-input bg-background px-3 text-sm"
                  aria-label="Visible To"
                  value={selectedPartnerUserId}
                  onChange={(event) => setSelectedPartnerUserId(event.target.value)}
                >
                  <option value="">All members</option>
                  {scopedMemberOptions.map((member) => (
                    <option key={member.id} value={member.user_id}>
                      {member.user_name || member.user_email || `User #${member.user_id}`}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Expiry</label>
                <select
                  className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                  aria-label="Share Expiry"
                  value={expirationDays}
                  onChange={(event) => setExpirationDays(event.target.value)}
                >
                  <option value="">No expiry</option>
                  <option value="7">7 days</option>
                  <option value="14">14 days</option>
                  <option value="30">30 days</option>
                </select>
              </div>
              <label className="mb-1 flex h-9 items-center gap-2 rounded-md border border-input px-3 text-xs text-foreground">
                <input
                  type="checkbox"
                  aria-label="Require approval"
                  checked={requiresApproval}
                  onChange={(event) => setRequiresApproval(event.target.checked)}
                />
                Require approval
              </label>
              <Button
                size="sm"
                disabled={
                  isSharing ||
                  (shareDataType === "contract_feed"
                    ? !selectedContractFeedId
                    : !shareEntityId.trim())
                }
                onClick={async () => {
                  const entityId = Number.parseInt(
                    shareDataType === "contract_feed"
                      ? selectedContractFeedId
                      : shareEntityId,
                    10
                  );
                  if (!Number.isFinite(entityId) || entityId <= 0) return;
                  const expiresAt = expirationDays
                    ? new Date(Date.now() + Number.parseInt(expirationDays, 10) * 86_400_000)
                    : null;
                  setIsSharing(true);
                  try {
                    await collaborationApi.shareData(workspace.id, {
                      data_type: shareDataType,
                      entity_id: entityId,
                      requires_approval: requiresApproval,
                      partner_user_id: selectedPartnerUserId
                        ? Number.parseInt(selectedPartnerUserId, 10)
                        : null,
                      expires_at: expiresAt?.toISOString() ?? null,
                    });
                    setShareEntityId("");
                    setExpirationDays("");
                    setSelectedPartnerUserId("");
                    setRequiresApproval(false);
                    await load();
                  } catch {
                    /* handled by interceptor */
                  } finally {
                    setIsSharing(false);
                  }
                }}
              >
                Share
              </Button>
            </div>
          </div>

          {sharedData.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No data shared yet. Share RFP summaries, compliance matrices,
              contract feeds, or forecasts with workspace members.
            </p>
          )}
          {sharedData.map((sd) => (
            <div
              key={sd.id}
              data-testid={`shared-item-${sd.id}`}
              className="flex items-center justify-between gap-3 p-3 rounded-lg border border-border"
            >
              <div className="min-w-0 flex items-center gap-2">
                <Badge variant="outline">{sd.data_type.replace(/_/g, " ")}</Badge>
                <Badge variant={sd.approval_status === "approved" ? "default" : "secondary"}>
                  {sd.approval_status}
                </Badge>
                <div className="min-w-0">
                  <span className="block truncate text-sm text-muted-foreground">
                    {sd.label || `Entity #${sd.entity_id}`}
                  </span>
                  <span className="block truncate text-[11px] text-muted-foreground">
                    {sd.partner_user_id
                      ? `Scoped to user #${sd.partner_user_id}`
                      : "Visible to all members"}{" "}
                    &middot; {formatExpiration(sd.expires_at)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-1">
                {sd.approval_status === "pending" && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => {
                      await collaborationApi.approveSharedData(workspace.id, sd.id);
                      await load();
                    }}
                  >
                    Approve
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={async () => {
                    await collaborationApi.unshareData(workspace.id, sd.id);
                    load();
                  }}
                >
                  <Trash2 className="w-3 h-3" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function CollaborationPage() {
  const searchParams = useSearchParams();
  const [workspaces, setWorkspaces] = useState<SharedWorkspace[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [showFeed, setShowFeed] = useState(false);
  const [feedProposalId, setFeedProposalId] = useState<number | null>(null);

  const loadWorkspaces = useCallback(async () => {
    setLoading(true);
    try {
      const data = await collaborationApi.listWorkspaces();
      setWorkspaces(data);
      if (data.length > 0 && !selectedId) {
        setSelectedId(data[0].id);
      }
    } catch {
      /* handled */
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    loadWorkspaces();
  }, [loadWorkspaces]);

  useEffect(() => {
    const rawWorkspaceId = searchParams.get("workspace");
    if (!rawWorkspaceId) return;
    const requestedWorkspaceId = Number.parseInt(rawWorkspaceId, 10);
    if (Number.isNaN(requestedWorkspaceId)) return;
    if (workspaces.some((workspace) => workspace.id === requestedWorkspaceId)) {
      setSelectedId(requestedWorkspaceId);
    }
  }, [searchParams, workspaces]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      const ws = await collaborationApi.createWorkspace({
        name: newName.trim(),
        description: newDesc.trim() || null,
      });
      setWorkspaces((prev) => [...prev, ws]);
      setSelectedId(ws.id);
      setShowCreate(false);
      setNewName("");
      setNewDesc("");
    } catch {
      /* handled */
    }
  };

  const selectedWorkspace = workspaces.find((w) => w.id === selectedId) || null;

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Collaboration"
        description="Share workspaces and data with teaming partners"
        actions={
          <div className="flex gap-2">
            <Button
              variant={showFeed ? "default" : "outline"}
              onClick={() => setShowFeed((p) => !p)}
            >
              <Activity className="w-4 h-4 mr-2" /> Activity
            </Button>
            <Button onClick={() => setShowCreate(true)}>
              <Share2 className="w-4 h-4 mr-2" /> New Workspace
            </Button>
          </div>
        }
      />

      <div className="flex-1 overflow-auto p-6">
        {loading ? (
          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-4 space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 w-full rounded bg-muted animate-pulse" />
              ))}
            </div>
            <div className="col-span-8">
              <div className="h-64 w-full rounded bg-muted animate-pulse" />
            </div>
          </div>
        ) : (
          <>
            {/* Create workspace modal */}
            {showCreate && (
              <div className="mb-6 p-4 rounded-lg border border-primary/30 bg-primary/5">
                <h3 className="text-sm font-semibold text-foreground mb-3">
                  Create Workspace
                </h3>
                <div className="space-y-3">
                  <input
                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    placeholder="Workspace name"
                    value={newName}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewName(e.target.value)}
                  />
                  <input
                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    placeholder="Description (optional)"
                    value={newDesc}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewDesc(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <Button size="sm" onClick={handleCreate} disabled={!newName.trim()}>
                      Create
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setShowCreate(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </div>
            )}

            <div className={`grid gap-6 ${showFeed ? "grid-cols-12" : "grid-cols-12"}`}>
              {/* Sidebar: workspace list */}
              <div className={showFeed ? "col-span-3" : "col-span-4"}>
                <WorkspaceList
                  workspaces={workspaces}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                  onCreate={() => setShowCreate(true)}
                />
              </div>

              {/* Detail */}
              <div className={showFeed ? "col-span-6" : "col-span-8"}>
                {selectedWorkspace ? (
                  <WorkspaceDetail
                    workspace={selectedWorkspace}
                    onRefresh={loadWorkspaces}
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                    <Share2 className="w-12 h-12 mb-3 opacity-30" />
                    <p className="text-sm">
                      Select or create a workspace to get started
                    </p>
                  </div>
                )}
              </div>

              {/* Activity Feed Sidebar */}
              {showFeed && (
                <div className="col-span-3 space-y-3">
                  <div className="flex items-center gap-2 mb-2">
                    <label className="text-xs text-muted-foreground">Proposal ID:</label>
                    <input
                      type="number"
                      className="h-7 w-20 rounded border border-input bg-background px-2 text-xs"
                      value={feedProposalId ?? ""}
                      onChange={(e) =>
                        setFeedProposalId(e.target.value ? Number(e.target.value) : null)
                      }
                      placeholder="ID"
                    />
                  </div>
                  {feedProposalId ? (
                    <ActivityFeed proposalId={feedProposalId} />
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      Enter a proposal ID to view its activity feed.
                    </p>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
