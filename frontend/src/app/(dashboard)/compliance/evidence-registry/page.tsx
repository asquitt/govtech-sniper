"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { complianceApi } from "@/lib/api/compliance";
import type {
  ComplianceCheckpointEvidenceItem,
  ComplianceRegistryEvidenceItem,
  ComplianceCheckpointSignoff,
  ComplianceReadinessCheckpoint,
  ComplianceReadinessCheckpointSnapshot,
} from "@/types/compliance";

export default function ComplianceEvidenceRegistryPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkpoints, setCheckpoints] = useState<ComplianceReadinessCheckpoint[]>([]);
  const [selectedCheckpointId, setSelectedCheckpointId] = useState<string>("");
  const [evidenceItems, setEvidenceItems] = useState<ComplianceCheckpointEvidenceItem[]>([]);
  const [registryEvidence, setRegistryEvidence] = useState<ComplianceRegistryEvidenceItem[]>([]);
  const [registryEvidenceScope, setRegistryEvidenceScope] =
    useState<"mine" | "organization">("organization");
  const [selectedRegistryEvidenceId, setSelectedRegistryEvidenceId] = useState("");
  const [linkEvidenceNotes, setLinkEvidenceNotes] = useState("");
  const [isLinking, setIsLinking] = useState(false);
  const [isUpdatingStatusId, setIsUpdatingStatusId] = useState<number | null>(null);
  const [signoff, setSignoff] = useState<ComplianceCheckpointSignoff | null>(null);
  const [isSavingSignoff, setIsSavingSignoff] = useState(false);
  const [canManage, setCanManage] = useState(false);

  const loadRegistry = useCallback(async (checkpointId: string) => {
    try {
      const [items, signoffData] = await Promise.all([
        complianceApi.listCheckpointEvidence(checkpointId),
        complianceApi.getCheckpointSignoff(checkpointId),
      ]);
      setEvidenceItems(items);
      setSignoff(signoffData);
    } catch {
      setError("Failed to load checkpoint evidence registry.");
    }
  }, []);

  const loadEvidenceCatalog = useCallback(
    async (scope: "mine" | "organization") => {
      try {
        const evidence = await complianceApi.listRegistryEvidence({
          scope,
          limit: 200,
        });
        setRegistryEvidence(evidence);
        if (evidence.length > 0) {
          setSelectedRegistryEvidenceId(String(evidence[0].id));
        } else {
          setSelectedRegistryEvidenceId("");
        }
      } catch {
        setError("Failed to load evidence catalog.");
      }
    },
    []
  );

  const bootstrap = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [checkpointSnapshot, trustCenter] = await Promise.all([
        complianceApi.getReadinessCheckpoints(),
        complianceApi.getTrustCenter(),
      ]);
      const checkpointData = (checkpointSnapshot as ComplianceReadinessCheckpointSnapshot).checkpoints;
      setCheckpoints(checkpointData);
      setCanManage(trustCenter.can_manage_policy);
      const initialScope =
        trustCenter.organization_id !== null ? "organization" : "mine";
      setRegistryEvidenceScope(initialScope);
      if (checkpointData.length > 0) {
        const firstId = checkpointData[0].checkpoint_id;
        setSelectedCheckpointId(firstId);
      }
    } catch {
      setError("Failed to bootstrap compliance evidence registry.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    if (!selectedCheckpointId) return;
    loadRegistry(selectedCheckpointId);
  }, [selectedCheckpointId, loadRegistry]);

  useEffect(() => {
    if (!registryEvidenceScope) return;
    loadEvidenceCatalog(registryEvidenceScope);
  }, [registryEvidenceScope, loadEvidenceCatalog]);

  const selectedCheckpoint = checkpoints.find(
    (checkpoint) => checkpoint.checkpoint_id === selectedCheckpointId
  );

  const handleLinkEvidence = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedCheckpointId || !canManage) return;
    const evidenceId = Number.parseInt(selectedRegistryEvidenceId, 10);
    if (!Number.isFinite(evidenceId) || evidenceId <= 0) {
      setError("Select a valid evidence artifact.");
      return;
    }
    setIsLinking(true);
    setError(null);
    try {
      await complianceApi.createCheckpointEvidence(selectedCheckpointId, {
        evidence_id: evidenceId,
        notes: linkEvidenceNotes || undefined,
      });
      setLinkEvidenceNotes("");
      await loadRegistry(selectedCheckpointId);
    } catch {
      setError("Failed to link evidence to checkpoint.");
    } finally {
      setIsLinking(false);
    }
  };

  const updateEvidenceStatus = async (
    linkId: number,
    status: "submitted" | "accepted" | "rejected"
  ) => {
    if (!selectedCheckpointId || !canManage) return;
    setIsUpdatingStatusId(linkId);
    setError(null);
    try {
      await complianceApi.updateCheckpointEvidence(selectedCheckpointId, linkId, { status });
      await loadRegistry(selectedCheckpointId);
    } catch {
      setError("Failed to update evidence status.");
    } finally {
      setIsUpdatingStatusId(null);
    }
  };

  const saveSignoff = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedCheckpointId || !canManage || !signoff) return;
    setIsSavingSignoff(true);
    setError(null);
    try {
      const updated = await complianceApi.upsertCheckpointSignoff(selectedCheckpointId, {
        status: signoff.status,
        assessor_name: signoff.assessor_name,
        assessor_org: signoff.assessor_org ?? undefined,
        notes: signoff.notes ?? undefined,
      });
      setSignoff(updated);
    } catch {
      setError("Failed to update assessor sign-off.");
    } finally {
      setIsSavingSignoff(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <Header
          title="Compliance Evidence Registry"
          description="Checkpoint evidence and assessor sign-off workflows"
        />
        <div className="flex-1 p-6">
          <div className="animate-pulse h-40 rounded-lg bg-muted" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Compliance Evidence Registry"
        description="Checkpoint evidence and assessor sign-off workflows"
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        <Card>
          <CardHeader>
            <CardTitle>Checkpoint</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <select
              aria-label="Readiness checkpoint"
              className="h-9 w-full max-w-xl rounded-md border border-input bg-background px-3 text-sm"
              value={selectedCheckpointId}
              onChange={(event) => setSelectedCheckpointId(event.target.value)}
            >
              {checkpoints.map((checkpoint) => (
                <option key={checkpoint.checkpoint_id} value={checkpoint.checkpoint_id}>
                  {checkpoint.title}
                </option>
              ))}
            </select>
            {selectedCheckpoint ? (
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <Badge variant="outline">{selectedCheckpoint.program_id.replaceAll("_", " ")}</Badge>
                {selectedCheckpoint.assessor_signoff_status ? (
                  <Badge
                    variant={
                      selectedCheckpoint.assessor_signoff_status === "approved"
                        ? "default"
                        : selectedCheckpoint.assessor_signoff_status === "rejected"
                          ? "destructive"
                          : "secondary"
                    }
                  >
                    Sign-off: {selectedCheckpoint.assessor_signoff_status}
                  </Badge>
                ) : null}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Evidence Links</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <label className="text-xs text-muted-foreground">Evidence scope</label>
              <select
                aria-label="Evidence scope"
                className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                value={registryEvidenceScope}
                onChange={(event) =>
                  setRegistryEvidenceScope(event.target.value as "mine" | "organization")
                }
              >
                <option value="organization">organization</option>
                <option value="mine">mine</option>
              </select>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => loadEvidenceCatalog(registryEvidenceScope)}
              >
                Refresh Catalog
              </Button>
            </div>
            {canManage ? (
              <form className="grid gap-2 md:grid-cols-3" onSubmit={handleLinkEvidence}>
                <select
                  aria-label="Evidence catalog selection"
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={selectedRegistryEvidenceId}
                  onChange={(event) => setSelectedRegistryEvidenceId(event.target.value)}
                >
                  {registryEvidence.length === 0 ? (
                    <option value="">No evidence artifacts found</option>
                  ) : null}
                  {registryEvidence.map((item) => (
                    <option key={item.id} value={item.id}>
                      #{item.id} · {item.title} ({item.evidence_type})
                    </option>
                  ))}
                </select>
                <input
                  aria-label="Evidence notes"
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={linkEvidenceNotes}
                  onChange={(event) => setLinkEvidenceNotes(event.target.value)}
                  placeholder="Notes (optional)"
                />
                <Button
                  type="submit"
                  disabled={
                    isLinking || !selectedCheckpointId || !selectedRegistryEvidenceId
                  }
                >
                  {isLinking ? "Linking..." : "Link Evidence"}
                </Button>
              </form>
            ) : (
              <p className="text-xs text-muted-foreground">
                Read-only: org owners/admins can link evidence and update statuses.
              </p>
            )}

            {evidenceItems.length === 0 ? (
              <p className="text-sm text-muted-foreground">No linked evidence for this checkpoint.</p>
            ) : (
              evidenceItems.map((item) => (
                <div key={item.link_id} className="rounded-lg border border-border p-3 space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium">{item.title}</p>
                    <Badge variant="outline">{item.status}</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Evidence #{item.evidence_id} · Type {item.evidence_type}
                  </p>
                  {item.reviewer_notes ? (
                    <p className="text-xs text-muted-foreground">Reviewer notes: {item.reviewer_notes}</p>
                  ) : null}
                  {canManage ? (
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={isUpdatingStatusId === item.link_id}
                        onClick={() => updateEvidenceStatus(item.link_id, "submitted")}
                      >
                        Mark Submitted
                      </Button>
                      <Button
                        size="sm"
                        disabled={isUpdatingStatusId === item.link_id}
                        onClick={() => updateEvidenceStatus(item.link_id, "accepted")}
                      >
                        Accept
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        disabled={isUpdatingStatusId === item.link_id}
                        onClick={() => updateEvidenceStatus(item.link_id, "rejected")}
                      >
                        Reject
                      </Button>
                    </div>
                  ) : null}
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Assessor Sign-Off</CardTitle>
          </CardHeader>
          <CardContent>
            {signoff ? (
              <form className="space-y-3" onSubmit={saveSignoff}>
                <div className="grid gap-3 md:grid-cols-2">
                  <select
                    aria-label="Sign-off status"
                    className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={signoff.status}
                    onChange={(event) =>
                      setSignoff((prev) =>
                        prev
                          ? {
                              ...prev,
                              status: event.target.value as
                                | "pending"
                                | "approved"
                                | "rejected",
                            }
                          : prev
                      )
                    }
                    disabled={!canManage || isSavingSignoff}
                  >
                    <option value="pending">pending</option>
                    <option value="approved">approved</option>
                    <option value="rejected">rejected</option>
                  </select>
                  <input
                    aria-label="Assessor name"
                    className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={signoff.assessor_name}
                    onChange={(event) =>
                      setSignoff((prev) =>
                        prev ? { ...prev, assessor_name: event.target.value } : prev
                      )
                    }
                    disabled={!canManage || isSavingSignoff}
                  />
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <input
                    aria-label="Assessor organization"
                    className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={signoff.assessor_org ?? ""}
                    onChange={(event) =>
                      setSignoff((prev) =>
                        prev ? { ...prev, assessor_org: event.target.value } : prev
                      )
                    }
                    placeholder="Assessor organization"
                    disabled={!canManage || isSavingSignoff}
                  />
                  <input
                    aria-label="Sign-off notes"
                    className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={signoff.notes ?? ""}
                    onChange={(event) =>
                      setSignoff((prev) =>
                        prev ? { ...prev, notes: event.target.value } : prev
                      )
                    }
                    placeholder="Notes"
                    disabled={!canManage || isSavingSignoff}
                  />
                </div>
                {canManage ? (
                  <Button type="submit" disabled={isSavingSignoff || !selectedCheckpointId}>
                    {isSavingSignoff ? "Saving..." : "Save Sign-Off"}
                  </Button>
                ) : null}
              </form>
            ) : (
              <p className="text-sm text-muted-foreground">No sign-off data loaded.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
