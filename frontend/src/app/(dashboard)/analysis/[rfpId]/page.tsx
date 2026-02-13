"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { AlertCircle, Loader2 } from "lucide-react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ComplianceMatrix } from "@/components/analysis/compliance-matrix";
import { DraftPreview } from "@/components/analysis/draft-preview";
import { rfpApi, analysisApi, draftApi, exportApi } from "@/lib/api";
import { getApiErrorMessage } from "@/lib/api/error";
import type { ComplianceRequirement, GeneratedContent, RFP } from "@/types";
import { AnalysisHeader } from "./_components/analysis-header";
import { StatusBar } from "./_components/status-bar";
import { EditRequirementForm, initEditForm } from "./_components/edit-requirement-form";
import { CreateRequirementForm } from "./_components/create-requirement-form";
import { ShredView } from "./_components/shred-view";

export default function AnalysisPage() {
  const params = useParams();
  const rfpId = parseInt(params.rfpId as string);

  const [rfp, setRfp] = useState<RFP | null>(null);
  const [requirements, setRequirements] = useState<ComplianceRequirement[]>([]);
  const [selectedRequirement, setSelectedRequirement] = useState<ComplianceRequirement | undefined>();
  const [generatedContent, setGeneratedContent] = useState<GeneratedContent | undefined>();
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatingId, setGeneratingId] = useState<string | undefined>();
  const [isExporting, setIsExporting] = useState(false);
  const [activeProposalId, setActiveProposalId] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"list" | "shred">("list");
  const [isEditingRequirement, setIsEditingRequirement] = useState(false);
  const [showCreateRequirement, setShowCreateRequirement] = useState(false);
  const [snapshotDiff, setSnapshotDiff] = useState<{
    from_snapshot_id: number;
    to_snapshot_id: number;
    changes: { field: string; before?: string | null; after?: string | null }[];
    summary_from: Record<string, unknown>;
    summary_to: Record<string, unknown>;
  } | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setLoadError(null);
      const rfpData = await rfpApi.get(rfpId);
      setRfp(rfpData);
      setRequirements([]);
      setSnapshotDiff(null);

      const matrixData = await analysisApi.getComplianceMatrix(rfpId).catch(() => null);
      if (matrixData?.requirements) {
        setRequirements(matrixData.requirements);
      }

      const snapshots = await rfpApi.getSnapshots(rfpId, { limit: 2 }).catch(() => []);
      if (snapshots.length >= 2) {
        try {
          const diff = await rfpApi.getSnapshotDiff(rfpId);
          setSnapshotDiff(diff);
        } catch {
          setSnapshotDiff(null);
        }
      }
    } catch (err) {
      console.error("Failed to load RFP:", err);
      setLoadError("Failed to load RFP data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [rfpId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSelectRequirement = (requirement: ComplianceRequirement) => {
    setSelectedRequirement(requirement);
    if (requirement.is_addressed && requirement.generated_content) {
      setGeneratedContent(requirement.generated_content as GeneratedContent);
    } else {
      setGeneratedContent(undefined);
    }
  };

  const handleGenerate = async (requirement: ComplianceRequirement) => {
    setSelectedRequirement(requirement);
    setIsGenerating(true);
    setGeneratingId(requirement.id);
    setGeneratedContent(undefined);
    setActionError(null);

    try {
      const proposalTitle = rfp?.title
        ? `Proposal for ${rfp.title}`
        : `Proposal for RFP ${rfpId}`;
      const proposals = await draftApi.listProposals({ rfp_id: rfpId });
      const proposal =
        proposals[0] ?? (await draftApi.createProposal(rfpId, proposalTitle));
      setActiveProposalId(proposal.id);
      const sections = await draftApi.listSections(proposal.id);

      if (!sections.some((section) => section.requirement_id === requirement.id)) {
        await draftApi.generateFromMatrix(proposal.id);
      }

      const result = await draftApi.generateSection(requirement.id, {
        requirement_id: requirement.id,
        rfp_id: rfpId,
      });

      const refreshGeneratedResult = async () => {
        const matrixData = await analysisApi.getComplianceMatrix(rfpId);
        if (matrixData && matrixData.requirements) {
          setRequirements(matrixData.requirements);
          const updated = matrixData.requirements.find(
            (r: ComplianceRequirement) => r.id === requirement.id
          );
          if (updated?.generated_content) {
            setGeneratedContent(updated.generated_content as GeneratedContent);
            return;
          }
        }
        const refreshedSections = await draftApi.listSections(proposal.id);
        const generatedSection = refreshedSections.find(
          (section) => section.requirement_id === requirement.id
        );
        if (generatedSection?.generated_content) {
          setGeneratedContent(generatedSection.generated_content as GeneratedContent);
        }
      };

      if (result.status === "completed") {
        await refreshGeneratedResult();
        return;
      }

      let completed = false;
      let pollCount = 0;
      const maxPolls = 30;
      while (!completed && pollCount < maxPolls) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        const status = await draftApi.getGenerationStatus(result.task_id);
        pollCount += 1;
        if (status.status === "completed") {
          completed = true;
          await refreshGeneratedResult();
        } else if (status.status === "failed") {
          completed = true;
          setActionError(status.error || "Generation failed. Please try again.");
        }
      }
      if (!completed) {
        setActionError("Generation timed out. Please retry.");
      }
    } catch (err) {
      console.error("Generation failed:", err);
      setActionError(
        getApiErrorMessage(err, "Failed to generate content. Please try again.")
      );
    } finally {
      setIsGenerating(false);
      setGeneratingId(undefined);
    }
  };

  const handleRegenerate = () => {
    if (selectedRequirement) handleGenerate(selectedRequirement);
  };

  const handleApprove = async () => {
    if (!selectedRequirement) return;
    try {
      const updated = await analysisApi.updateRequirement(rfpId, selectedRequirement.id, {
        is_addressed: true,
        status: "addressed",
      });
      setRequirements(updated.requirements);
    } catch (err) {
      console.error("Failed to update requirement", err);
      setActionError("Failed to update requirement status.");
    }
  };

  const handleExport = async () => {
    if (!rfp) return;
    try {
      setIsExporting(true);
      setActionError(null);
      let proposalId = activeProposalId;
      if (!proposalId) {
        const proposals = await draftApi.listProposals({ rfp_id: rfpId });
        proposalId = proposals[0]?.id ?? null;
      }
      if (!proposalId) {
        setActionError("Create a proposal draft before exporting.");
        return;
      }
      const blob = await exportApi.exportProposalDocx(proposalId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `proposal_${rfp.solicitation_number || rfp.id}.docx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Export failed:", err);
      setActionError("Failed to export proposal. Please try again.");
    } finally {
      setIsExporting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Loading..." description="Fetching RFP data" />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (loadError || !rfp) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Error" description="Unable to load RFP" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
            <p className="text-destructive mb-4">{loadError || "RFP not found"}</p>
            <Button asChild>
              <Link href="/opportunities">Back to Opportunities</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <AnalysisHeader
        rfp={rfp}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onAddRequirement={() => setShowCreateRequirement(true)}
        onExport={handleExport}
        isExporting={isExporting}
      />

      <StatusBar rfp={rfp} requirements={requirements} />

      {actionError && (
        <div className="px-6 pt-4">
          <Card className="border border-destructive/30 bg-destructive/5">
            <CardContent className="p-3 flex items-center gap-2 text-destructive text-sm">
              <AlertCircle className="w-4 h-4" />
              {actionError}
            </CardContent>
          </Card>
        </div>
      )}

      {snapshotDiff && snapshotDiff.changes.length > 0 && (
        <div className="px-6 pt-4">
          <Card className="border border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    Latest Opportunity Changes
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Comparing snapshots {snapshotDiff.from_snapshot_id} &rarr; {snapshotDiff.to_snapshot_id}
                  </p>
                </div>
              </div>
              <div className="grid gap-3">
                {snapshotDiff.changes.map((change, index) => (
                  <div
                    key={`${change.field}-${index}`}
                    className="grid grid-cols-3 gap-3 text-xs border border-border rounded-lg p-3"
                  >
                    <div className="text-muted-foreground">
                      <span className="font-medium text-foreground">{change.field}</span>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Before</p>
                      <p className="text-foreground">{change.before || "\u2014"}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">After</p>
                      <p className="text-foreground">{change.after || "\u2014"}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {isEditingRequirement && selectedRequirement && (
        <EditRequirementForm
          rfpId={rfpId}
          requirement={selectedRequirement}
          initialForm={initEditForm(selectedRequirement)}
          onSaved={(reqs, refreshed) => {
            setRequirements(reqs);
            if (refreshed) setSelectedRequirement(refreshed);
            setIsEditingRequirement(false);
          }}
          onDeleted={() => {
            setRequirements((prev) =>
              prev.filter((r) => r.id !== selectedRequirement.id)
            );
            setSelectedRequirement(undefined);
            setIsEditingRequirement(false);
          }}
          onCancel={() => setIsEditingRequirement(false)}
          onError={(msg) => setActionError(msg)}
        />
      )}

      {showCreateRequirement && (
        <CreateRequirementForm
          rfpId={rfpId}
          onCreated={(reqs) => {
            setRequirements(reqs);
            setShowCreateRequirement(false);
          }}
          onCancel={() => setShowCreateRequirement(false)}
          onError={(msg) => setActionError(msg)}
        />
      )}

      {viewMode === "list" ? (
        <div className="flex-1 flex overflow-hidden">
          <div className="w-1/2 border-r border-border">
            <ComplianceMatrix
              requirements={requirements}
              selectedId={selectedRequirement?.id}
              onSelect={handleSelectRequirement}
              onGenerate={handleGenerate}
              isGenerating={isGenerating}
              generatingId={generatingId}
            />
          </div>
          <div className="w-1/2">
            <DraftPreview
              requirement={selectedRequirement}
              generatedContent={generatedContent}
              isGenerating={isGenerating}
              onRegenerate={handleRegenerate}
              onApprove={handleApprove}
              onEdit={() => {
                if (selectedRequirement) setIsEditingRequirement(true);
              }}
            />
          </div>
        </div>
      ) : (
        <ShredView
          requirements={requirements}
          isGenerating={isGenerating}
          generatingId={generatingId}
          onSelectRequirement={handleSelectRequirement}
          onGenerate={handleGenerate}
          onSwitchToList={() => setViewMode("list")}
        />
      )}
    </div>
  );
}
