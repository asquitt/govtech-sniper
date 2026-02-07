"use client";

import React, { useEffect, useState, useCallback } from "react";
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
} from "lucide-react";
import { collaborationApi } from "@/lib/api";
import type {
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

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [m, i, s] = await Promise.all([
        collaborationApi.listMembers(workspace.id),
        collaborationApi.listInvitations(workspace.id).catch(() => [] as WorkspaceInvitation[]),
        collaborationApi.listSharedData(workspace.id),
      ]);
      setMembers(m);
      setInvitations(i);
      setSharedData(s);
    } catch {
      /* handled */
    } finally {
      setLoading(false);
    }
  }, [workspace.id]);

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
      <div>
        <h2 className="text-lg font-semibold text-foreground">{workspace.name}</h2>
        {workspace.description && (
          <p className="text-sm text-muted-foreground">{workspace.description}</p>
        )}
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
            <div
              key={inv.id}
              className="flex items-center justify-between p-3 rounded-lg border border-border"
            >
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
          ))}
        </div>
      )}

      {/* Shared Data Tab */}
      {activeTab === "data" && (
        <div className="space-y-2">
          {sharedData.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No data shared yet. Share RFP summaries, compliance matrices, or
              forecasts with workspace members.
            </p>
          )}
          {sharedData.map((sd) => (
            <div
              key={sd.id}
              className="flex items-center justify-between p-3 rounded-lg border border-border"
            >
              <div className="flex items-center gap-2">
                <Badge variant="outline">{sd.data_type.replace(/_/g, " ")}</Badge>
                <span className="text-sm text-muted-foreground">
                  Entity #{sd.entity_id}
                </span>
              </div>
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
  }, []);

  useEffect(() => {
    loadWorkspaces();
  }, [loadWorkspaces]);

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
