"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { complianceApi } from "@/lib/api/compliance";
import type {
  ComplianceCheckpointEvidenceItem,
  ComplianceRegistryEvidenceItem,
  ComplianceCheckpointSignoff,
  ComplianceReadinessCheckpoint,
  ComplianceReadinessCheckpointSnapshot,
} from "@/types/compliance";
import { CheckpointSelector } from "./_components/checkpoint-selector";
import { EvidenceLinksCard } from "./_components/evidence-links-card";
import { AssessorSignoffCard } from "./_components/assessor-signoff-card";

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

        <CheckpointSelector
          checkpoints={checkpoints}
          selectedCheckpointId={selectedCheckpointId}
          onSelect={setSelectedCheckpointId}
        />

        <EvidenceLinksCard
          evidenceItems={evidenceItems}
          registryEvidence={registryEvidence}
          registryEvidenceScope={registryEvidenceScope}
          selectedRegistryEvidenceId={selectedRegistryEvidenceId}
          linkEvidenceNotes={linkEvidenceNotes}
          isLinking={isLinking}
          isUpdatingStatusId={isUpdatingStatusId}
          canManage={canManage}
          selectedCheckpointId={selectedCheckpointId}
          onScopeChange={setRegistryEvidenceScope}
          onRefreshCatalog={() => loadEvidenceCatalog(registryEvidenceScope)}
          onSelectedEvidenceChange={setSelectedRegistryEvidenceId}
          onNotesChange={setLinkEvidenceNotes}
          onLinkEvidence={handleLinkEvidence}
          onUpdateStatus={updateEvidenceStatus}
        />

        <AssessorSignoffCard
          signoff={signoff}
          canManage={canManage}
          isSavingSignoff={isSavingSignoff}
          selectedCheckpointId={selectedCheckpointId}
          onSignoffChange={setSignoff}
          onSave={saveSignoff}
        />
      </div>
    </div>
  );
}
