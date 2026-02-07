"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { adminApi } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import type {
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

export default function AdminPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [org, setOrg] = useState<OrganizationDetails | null>(null);
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [usage, setUsage] = useState<OrgUsageAnalytics | null>(null);
  const [auditEvents, setAuditEvents] = useState<OrgAuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [orgData, membersData, usageData, auditData] = await Promise.all([
        adminApi.getOrganization(),
        adminApi.listMembers(),
        adminApi.getUsageAnalytics(30),
        adminApi.getAuditLog({ limit: 50 }),
      ]);
      setOrg(orgData);
      setMembers(membersData.members);
      setUsage(usageData);
      setAuditEvents(auditData.events);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load admin data";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

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

  if (error && !loading) {
    return (
      <div className="flex flex-col h-full">
        <Header
          title="Admin Console"
          description="Organization management, user roles, and audit logging"
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-2">
            <p className="text-sm text-muted-foreground">
              {error.includes("403")
                ? "You need admin or owner access to view this page."
                : "Could not load admin data. Make sure you belong to an organization."}
            </p>
          </div>
        </div>
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
            <UsageCard usage={usage} loading={loading} />
            <AuditLogCard events={auditEvents} loading={loading} />
          </div>
        </div>
      </div>
    </div>
  );
}
