"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { adminApi } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import type {
  AdminCapabilityHealth,
  OrgMemberInvitation,
  OrganizationDetails,
  OrgMember,
  OrgUsageAnalytics,
  OrgAuditEvent,
  OrgRole,
} from "@/types";
import { OrgOverview } from "./_components/OrgOverview";
import { MembersTable } from "./_components/MembersTable";
import { UsageCard } from "./_components/UsageCard";
import { AuditLogCard } from "./_components/AuditLogCard";
import { CapabilityHealthCard } from "./_components/CapabilityHealthCard";
import { SecurityControlsCard } from "./_components/SecurityControlsCard";
import { InvitationsCard } from "./_components/InvitationsCard";
import { OrgBootstrapForm } from "./_components/OrgBootstrapForm";

type OrgSecurityPolicyKey =
  | "require_step_up_for_sensitive_exports"
  | "require_step_up_for_sensitive_shares"
  | "apply_cui_watermark_to_sensitive_exports"
  | "apply_cui_redaction_to_sensitive_exports";

export default function AdminPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [org, setOrg] = useState<OrganizationDetails | null>(null);
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [invitations, setInvitations] = useState<OrgMemberInvitation[]>([]);
  const [usage, setUsage] = useState<OrgUsageAnalytics | null>(null);
  const [auditEvents, setAuditEvents] = useState<OrgAuditEvent[]>([]);
  const [capabilityHealth, setCapabilityHealth] =
    useState<AdminCapabilityHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [bootstrapOrgName, setBootstrapOrgName] = useState("");
  const [bootstrapOrgSlug, setBootstrapOrgSlug] = useState("");
  const [bootstrapOrgDomain, setBootstrapOrgDomain] = useState("");
  const [bootstrapBillingEmail, setBootstrapBillingEmail] = useState("");
  const [bootstrapSubmitting, setBootstrapSubmitting] = useState(false);
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<OrgRole>("member");
  const [inviteDays, setInviteDays] = useState(7);
  const [inviteSubmitting, setInviteSubmitting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [policySaving, setPolicySaving] = useState<OrgSecurityPolicyKey | null>(null);
  const [policyError, setPolicyError] = useState<string | null>(null);

  const toSlug = (value: string): string =>
    value
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 64);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        orgData,
        membersData,
        invitationsData,
        usageData,
        auditData,
        capabilityHealthData,
      ] =
        await Promise.all([
          adminApi.getOrganization(),
          adminApi.listMembers(),
          adminApi.listMemberInvitations().catch(
            () => [] as OrgMemberInvitation[]
          ),
          adminApi.getUsageAnalytics(30),
          adminApi.getAuditLog({ limit: 50 }),
          adminApi.getCapabilityHealth(),
        ]);
      setOrg(orgData);
      setMembers(membersData.members);
      setInvitations(invitationsData);
      setUsage(usageData);
      setAuditEvents(auditData.events);
      setCapabilityHealth(capabilityHealthData);
    } catch (err) {
      const detail =
        typeof err === "object" &&
        err !== null &&
        "response" in err &&
        typeof (err as { response?: { data?: { detail?: unknown } } }).response
          ?.data?.detail === "string"
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      const message =
        detail ??
        (err instanceof Error ? err.message : "Failed to load admin data");
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleBootstrapOrganization = async (event: React.FormEvent) => {
    event.preventDefault();
    const trimmedName = bootstrapOrgName.trim();
    const slug = toSlug(bootstrapOrgSlug || trimmedName);
    if (!trimmedName || !slug) {
      setBootstrapError("Organization name and slug are required.");
      return;
    }

    setBootstrapSubmitting(true);
    setBootstrapError(null);
    try {
      await adminApi.createOrganization({
        name: trimmedName,
        slug,
        domain: bootstrapOrgDomain.trim() || undefined,
        billing_email: bootstrapBillingEmail.trim() || undefined,
      });
      setBootstrapOrgName("");
      setBootstrapOrgSlug("");
      setBootstrapOrgDomain("");
      setBootstrapBillingEmail("");
      await fetchAll();
    } catch (err) {
      const detail =
        typeof err === "object" &&
        err !== null &&
        "response" in err &&
        typeof (err as { response?: { data?: { detail?: unknown } } }).response
          ?.data?.detail === "string"
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setBootstrapError(
        detail ?? "Unable to create organization. Please try a different slug."
      );
    } finally {
      setBootstrapSubmitting(false);
    }
  };

  const handleRoleChange = async (userId: number, role: OrgRole) => {
    try {
      await adminApi.updateMemberRole(userId, role);
      setMembers((prev) =>
        prev.map((m) => (m.user_id === userId ? { ...m, role } : m))
      );
    } catch (err) {
      console.error("Failed to update role:", err);
    }
  };

  const handleDeactivate = async (userId: number) => {
    try {
      await adminApi.deactivateMember(userId);
      setMembers((prev) =>
        prev.map((m) => (m.user_id === userId ? { ...m, is_active: false } : m))
      );
    } catch (err) {
      console.error("Failed to deactivate:", err);
    }
  };

  const handleReactivate = async (userId: number) => {
    try {
      await adminApi.reactivateMember(userId);
      setMembers((prev) =>
        prev.map((m) => (m.user_id === userId ? { ...m, is_active: true } : m))
      );
    } catch (err) {
      console.error("Failed to reactivate:", err);
    }
  };

  const handleInviteMember = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!inviteEmail.trim()) {
      setInviteError("Email is required.");
      return;
    }
    setInviteSubmitting(true);
    setInviteError(null);
    try {
      await adminApi.inviteMember({
        email: inviteEmail.trim(),
        role: inviteRole,
        expires_in_days: inviteDays,
      });
      setInviteEmail("");
      await fetchAll();
    } catch (err) {
      const detail =
        typeof err === "object" &&
        err !== null &&
        "response" in err &&
        typeof (err as { response?: { data?: { detail?: unknown } } }).response
          ?.data?.detail === "string"
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setInviteError(detail ?? "Failed to invite member.");
    } finally {
      setInviteSubmitting(false);
    }
  };

  const handleActivateInvitation = async (invitationId: number) => {
    try {
      await adminApi.activateMemberInvitation(invitationId);
      await fetchAll();
    } catch (err) {
      const detail =
        typeof err === "object" &&
        err !== null &&
        "response" in err &&
        typeof (err as { response?: { data?: { detail?: unknown } } }).response
          ?.data?.detail === "string"
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setInviteError(detail ?? "Failed to activate invitation.");
    }
  };

  const handleRevokeInvitation = async (invitationId: number) => {
    try {
      await adminApi.revokeMemberInvitation(invitationId);
      await fetchAll();
    } catch (err) {
      const detail =
        typeof err === "object" &&
        err !== null &&
        "response" in err &&
        typeof (err as { response?: { data?: { detail?: unknown } } }).response
          ?.data?.detail === "string"
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setInviteError(detail ?? "Failed to revoke invitation.");
    }
  };

  const handleResendInvitation = async (invitationId: number) => {
    try {
      await adminApi.resendMemberInvitation(invitationId, inviteDays);
      await fetchAll();
    } catch (err) {
      const detail =
        typeof err === "object" &&
        err !== null &&
        "response" in err &&
        typeof (err as { response?: { data?: { detail?: unknown } } }).response
          ?.data?.detail === "string"
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setInviteError(detail ?? "Failed to resend invitation.");
    }
  };

  const handlePolicyToggle = async (
    policyKey: OrgSecurityPolicyKey,
    enabled: boolean
  ) => {
    if (!org) return;
    setPolicySaving(policyKey);
    setPolicyError(null);
    try {
      await adminApi.updateOrganization({ [policyKey]: enabled });
      setOrg((prev) =>
        prev ? { ...prev, [policyKey]: enabled } : prev
      );
    } catch (err) {
      const detail =
        typeof err === "object" &&
        err !== null &&
        "response" in err &&
        typeof (err as { response?: { data?: { detail?: unknown } } }).response
          ?.data?.detail === "string"
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setPolicyError(detail ?? "Failed to update security policy.");
    } finally {
      setPolicySaving(null);
    }
  };

  const invitationSlaClass = (slaState: OrgMemberInvitation["sla_state"]) => {
    if (slaState === "expired" || slaState === "aging") {
      return "bg-destructive/10 text-destructive";
    }
    if (slaState === "expiring") {
      return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
    }
    if (slaState === "completed") {
      return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
    }
    if (slaState === "revoked") {
      return "bg-muted text-muted-foreground";
    }
    return "bg-primary/10 text-primary";
  };

  const needsOrgBootstrap = error?.toLowerCase().includes("no organization membership");

  if (error && !loading) {
    return (
      <div className="flex flex-col h-full">
        <Header
          title="Admin Console"
          description="Organization management, user roles, and audit logging"
        />
        {needsOrgBootstrap ? (
          <OrgBootstrapForm
            name={bootstrapOrgName}
            slug={bootstrapOrgSlug}
            domain={bootstrapOrgDomain}
            billingEmail={bootstrapBillingEmail}
            submitting={bootstrapSubmitting}
            error={bootstrapError}
            onNameChange={setBootstrapOrgName}
            onSlugChange={setBootstrapOrgSlug}
            onDomainChange={setBootstrapOrgDomain}
            onBillingEmailChange={setBootstrapBillingEmail}
            onSubmit={handleBootstrapOrganization}
            toSlug={toSlug}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-2">
              <p className="text-sm text-muted-foreground">
                {error.includes("403")
                  ? "You need admin or owner access to view this page."
                  : "Could not load admin data. Make sure you belong to an organization."}
              </p>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Admin Console"
        description="Organization management, user roles, and audit logging"
      />
      <div className="flex-1 overflow-auto p-6 space-y-6">
        <OrgOverview org={org} loading={loading} />
        <CapabilityHealthCard
          capabilityHealth={capabilityHealth}
          loading={loading}
        />
        <SecurityControlsCard
          org={org}
          loading={loading}
          policySaving={policySaving}
          policyError={policyError}
          onPolicyToggle={handlePolicyToggle}
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <MembersTable
            members={members}
            loading={loading}
            onRoleChange={handleRoleChange}
            onDeactivate={handleDeactivate}
            onReactivate={handleReactivate}
            currentUserId={user?.id ?? 0}
          />
          <div className="space-y-6">
            <InvitationsCard
              invitations={invitations}
              inviteEmail={inviteEmail}
              inviteRole={inviteRole}
              inviteDays={inviteDays}
              inviteSubmitting={inviteSubmitting}
              inviteError={inviteError}
              onEmailChange={setInviteEmail}
              onRoleChange={setInviteRole}
              onDaysChange={setInviteDays}
              onSubmit={handleInviteMember}
              onActivate={handleActivateInvitation}
              onRevoke={handleRevokeInvitation}
              onResend={handleResendInvitation}
              invitationSlaClass={invitationSlaClass}
            />
            <UsageCard usage={usage} loading={loading} />
            <AuditLogCard events={auditEvents} loading={loading} />
          </div>
        </div>
      </div>
    </div>
  );
}
