"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Share2, Activity } from "lucide-react";
import { collaborationApi } from "@/lib/api";
import type { SharedWorkspace } from "@/types";
import { ActivityFeed } from "@/components/collaboration/activity-feed";
import { WorkspaceList } from "./_components/workspace-list";
import { WorkspaceDetail } from "./_components/workspace-detail";
import { WorkspaceCreateModal } from "./_components/workspace-create-modal";

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
            {showCreate && (
              <WorkspaceCreateModal
                newName={newName}
                newDesc={newDesc}
                onNewNameChange={setNewName}
                onNewDescChange={setNewDesc}
                onCreate={handleCreate}
                onCancel={() => setShowCreate(false)}
              />
            )}

            <div className={`grid gap-6 ${showFeed ? "grid-cols-12" : "grid-cols-12"}`}>
              <div className={showFeed ? "col-span-3" : "col-span-4"}>
                <WorkspaceList
                  workspaces={workspaces}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                  onCreate={() => setShowCreate(true)}
                />
              </div>

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
