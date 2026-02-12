"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Users } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { collaborationApi } from "@/lib/api";
import type { PortalView } from "@/types";

export default function CollaborationPortalPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = Number.parseInt(String(params.workspaceId), 10);
  const [portal, setPortal] = useState<PortalView | null>(null);
  const [workspaceOptions, setWorkspaceOptions] = useState<
    Array<{ id: number; name: string }>
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPortal = useCallback(async () => {
    if (!Number.isFinite(workspaceId) || workspaceId <= 0) {
      setError("Invalid workspace id.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const [data, workspaces] = await Promise.all([
        collaborationApi.getPortal(workspaceId),
        collaborationApi.listWorkspaces(),
      ]);
      setPortal(data);
      setWorkspaceOptions(workspaces.map((workspace) => ({ id: workspace.id, name: workspace.name })));
    } catch {
      setError("Unable to load partner portal.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    void loadPortal();
  }, [loadPortal]);

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Partner Portal"
        description="Read-only collaboration view for shared workspace artifacts."
        actions={
          <Button asChild variant="outline">
            <Link href={`/collaboration?workspace=${workspaceId}`}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Workspace
            </Link>
          </Button>
        }
      />

      <div className="flex-1 overflow-auto p-6">
        {loading && (
          <div className="h-40 rounded-lg bg-muted animate-pulse" />
        )}

        {!loading && error && (
          <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {!loading && portal && (
          <div className="space-y-4">
            <div className="rounded-lg border border-border bg-card p-4">
              <h2 className="text-lg font-semibold text-foreground">{portal.workspace_name}</h2>
              {portal.workspace_description && (
                <p className="text-sm text-muted-foreground mt-1">{portal.workspace_description}</p>
              )}
              {portal.rfp_title && (
                <p className="text-xs text-muted-foreground mt-2">
                  Opportunity: <span className="text-foreground">{portal.rfp_title}</span>
                </p>
              )}
              {workspaceOptions.length > 1 && (
                <div className="mt-3">
                  <label className="mb-1 block text-xs text-muted-foreground">
                    Switch Workspace
                  </label>
                  <select
                    aria-label="Switch Workspace"
                    className="h-9 min-w-64 rounded-md border border-input bg-background px-3 text-sm"
                    value={String(workspaceId)}
                    onChange={(event) => {
                      const nextWorkspaceId = Number.parseInt(event.target.value, 10);
                      if (!Number.isFinite(nextWorkspaceId) || nextWorkspaceId === workspaceId) {
                        return;
                      }
                      router.push(`/collaboration/portal/${nextWorkspaceId}`);
                    }}
                  >
                    {workspaceOptions.map((workspace) => (
                      <option key={workspace.id} value={workspace.id}>
                        {workspace.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="rounded-lg border border-border bg-card p-4 space-y-2">
              <h3 className="text-sm font-semibold text-foreground">Shared Artifacts</h3>
              {portal.shared_items.length === 0 ? (
                <p className="text-sm text-muted-foreground">No shared artifacts yet.</p>
              ) : (
                portal.shared_items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between rounded-md border border-border px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{item.data_type.replace(/_/g, " ")}</Badge>
                      <span className="text-xs text-muted-foreground">
                        {item.label || `Entity #${item.entity_id}`}
                      </span>
                    </div>
                    {item.expires_at && (
                      <span className="text-[11px] text-muted-foreground">
                        Expires {new Date(item.expires_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="rounded-lg border border-border bg-card p-4 space-y-2">
              <h3 className="text-sm font-semibold text-foreground">Workspace Members</h3>
              {portal.members.length === 0 ? (
                <p className="text-sm text-muted-foreground">No members available.</p>
              ) : (
                portal.members.map((member) => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between rounded-md border border-border px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      <Users className="w-4 h-4 text-primary" />
                      <span className="text-sm text-foreground">
                        {member.user_name || member.user_email || `User #${member.user_id}`}
                      </span>
                    </div>
                    <Badge variant="secondary">{member.role}</Badge>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
