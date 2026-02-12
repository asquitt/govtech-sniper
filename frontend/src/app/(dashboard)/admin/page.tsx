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

  const needsOrgBootstrap = error?.toLowerCase().includes("no organization membership");

  if (error && !loading) {
    return (
      <div className="flex flex-col h-full">
        <Header
          title="Admin Console"
          description="Organization management, user roles, and audit logging"
        />
        {needsOrgBootstrap ? (
          <div className="flex-1 p-6 overflow-auto">
            <div className="mx-auto max-w-xl rounded-lg border border-border p-5 space-y-4">
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">Set up your organization</p>
                <p className="text-xs text-muted-foreground">
                  Create an organization to enable admin access, member management, and audit logs.
                </p>
              </div>

              <form className="space-y-3" onSubmit={handleBootstrapOrganization}>
                <div className="space-y-1">
                  <label
                    htmlFor="bootstrap-org-name"
                    className="text-xs text-muted-foreground"
                  >
                    Organization name
                  </label>
                  <input
                    id="bootstrap-org-name"
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    placeholder="Acme GovTech"
                    value={bootstrapOrgName}
                    onChange={(event) => {
                      const value = event.target.value;
                      setBootstrapOrgName(value);
                      if (!bootstrapOrgSlug) {
                        setBootstrapOrgSlug(toSlug(value));
                      }
                    }}
                  />
                </div>

                <div className="space-y-1">
                  <label
                    htmlFor="bootstrap-org-slug"
                    className="text-xs text-muted-foreground"
                  >
                    Organization slug
                  </label>
                  <input
                    id="bootstrap-org-slug"
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    placeholder="acme-govtech"
                    value={bootstrapOrgSlug}
                    onChange={(event) => setBootstrapOrgSlug(toSlug(event.target.value))}
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label
                      htmlFor="bootstrap-org-domain"
                      className="text-xs text-muted-foreground"
                    >
                      Domain (optional)
                    </label>
                    <input
                      id="bootstrap-org-domain"
                      className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                      placeholder="acme.com"
                      value={bootstrapOrgDomain}
                      onChange={(event) => setBootstrapOrgDomain(event.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <label
                      htmlFor="bootstrap-org-billing-email"
                      className="text-xs text-muted-foreground"
                    >
                      Billing email (optional)
                    </label>
                    <input
                      id="bootstrap-org-billing-email"
                      className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                      placeholder="billing@acme.com"
                      value={bootstrapBillingEmail}
                      onChange={(event) => setBootstrapBillingEmail(event.target.value)}
                    />
                  </div>
                </div>

                {bootstrapError && <p className="text-xs text-destructive">{bootstrapError}</p>}

                <button
                  type="submit"
                  className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
                  disabled={bootstrapSubmitting}
                >
                  {bootstrapSubmitting ? "Creating..." : "Create Organization"}
                </button>
              </form>
            </div>
          </div>
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
            <div className="rounded-lg border border-border bg-card p-5 space-y-4">
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">Member Invitations</p>
                <p className="text-xs text-muted-foreground">
                  Invite users by email, then activate once they register.
                </p>
              </div>
              <form className="grid gap-2 md:grid-cols-4" onSubmit={handleInviteMember}>
                <input
                  aria-label="Invite member email"
                  className="md:col-span-2 rounded-md border border-border bg-background px-3 py-2 text-sm"
                  placeholder="new-member@example.com"
                  value={inviteEmail}
                  onChange={(event) => setInviteEmail(event.target.value)}
                />
                <select
                  aria-label="Invite role"
                  className="rounded-md border border-border bg-background px-3 py-2 text-sm"
                  value={inviteRole}
                  onChange={(event) => setInviteRole(event.target.value as OrgRole)}
                >
                  <option value="viewer">viewer</option>
                  <option value="member">member</option>
                  <option value="admin">admin</option>
                  <option value="owner">owner</option>
                </select>
                <div className="flex items-center gap-2">
                  <input
                    aria-label="Invitation expiration days"
                    type="number"
                    min={1}
                    max={30}
                    className="w-20 rounded-md border border-border bg-background px-2 py-2 text-sm"
                    value={inviteDays}
                    onChange={(event) =>
                      setInviteDays(Number.parseInt(event.target.value, 10) || 7)
                    }
                  />
                  <button
                    type="submit"
                    className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground"
                    disabled={inviteSubmitting}
                  >
                    {inviteSubmitting ? "Inviting..." : "Invite"}
                  </button>
                </div>
              </form>
              {inviteError ? <p className="text-xs text-destructive">{inviteError}</p> : null}
              <div className="space-y-2">
                {invitations.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No invitations yet.</p>
                ) : (
                  invitations.map((invitation) => (
                    <div
                      key={invitation.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border px-3 py-2"
                      data-testid={`org-invitation-${invitation.id}`}
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm text-foreground">{invitation.email}</p>
                        <p className="text-xs text-muted-foreground">
                          {invitation.role} · {invitation.status} · expires{" "}
                          {new Date(invitation.expires_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-muted-foreground">
                          {invitation.activation_ready
                            ? "Registered"
                            : "Awaiting registration"}
                        </span>
                        <button
                          type="button"
                          className="inline-flex h-8 items-center rounded-md border border-border px-2 text-xs"
                          disabled={
                            invitation.status !== "pending" || !invitation.activation_ready
                          }
                          onClick={() => handleActivateInvitation(invitation.id)}
                        >
                          Activate
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
            <UsageCard usage={usage} loading={loading} />
            <AuditLogCard events={auditEvents} loading={loading} />
          </div>
        </div>
      </div>
    </div>
  );
}
