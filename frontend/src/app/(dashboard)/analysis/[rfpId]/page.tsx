"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Download,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileText,
  List,
  Grid3X3,
  Plus,
  Pencil,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent } from "@/components/ui/card";
import { ComplianceMatrix } from "@/components/analysis/compliance-matrix";
import { DraftPreview } from "@/components/analysis/draft-preview";
import { rfpApi, analysisApi, draftApi, exportApi } from "@/lib/api";
import type { ComplianceRequirement, GeneratedContent, RFP } from "@/types";

export default function AnalysisPage() {
  const params = useParams();
  const rfpId = parseInt(params.rfpId as string);

  // State
  const [rfp, setRfp] = useState<RFP | null>(null);
  const [requirements, setRequirements] = useState<ComplianceRequirement[]>([]);
  const [selectedRequirement, setSelectedRequirement] = useState<ComplianceRequirement | undefined>();
  const [generatedContent, setGeneratedContent] = useState<GeneratedContent | undefined>();
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatingId, setGeneratingId] = useState<string | undefined>();
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"list" | "shred">("list");
  const [isEditingRequirement, setIsEditingRequirement] = useState(false);
  const [isSavingRequirement, setIsSavingRequirement] = useState(false);
  const [showCreateRequirement, setShowCreateRequirement] = useState(false);
  const [editForm, setEditForm] = useState({
    section: "",
    requirement_text: "",
    importance: "mandatory",
    category: "",
    notes: "",
    is_addressed: false,
    page_reference: "",
    keywords: "",
  });
  const [newRequirement, setNewRequirement] = useState({
    section: "",
    requirement_text: "",
    importance: "mandatory",
    category: "",
    notes: "",
    page_reference: "",
    keywords: "",
  });
  const [snapshotDiff, setSnapshotDiff] = useState<{
    from_snapshot_id: number;
    to_snapshot_id: number;
    changes: { field: string; before?: string | null; after?: string | null }[];
    summary_from: Record<string, unknown>;
    summary_to: Record<string, unknown>;
  } | null>(null);

  // Fetch RFP and requirements
  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const [rfpData, matrixData] = await Promise.all([
        rfpApi.get(rfpId),
        analysisApi.getComplianceMatrix(rfpId).catch(() => null),
      ]);

      setRfp(rfpData);

      if (matrixData && matrixData.requirements) {
        setRequirements(matrixData.requirements);
      }

      try {
        const diff = await rfpApi.getSnapshotDiff(rfpId);
        setSnapshotDiff(diff);
      } catch (diffErr) {
        setSnapshotDiff(null);
      }
    } catch (err) {
      console.error("Failed to load RFP:", err);
      setError("Failed to load RFP data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [rfpId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSelectRequirement = (requirement: ComplianceRequirement) => {
    setSelectedRequirement(requirement);
    setEditForm({
      section: requirement.section,
      requirement_text: requirement.requirement_text,
      importance: requirement.importance,
      category: requirement.category || "",
      notes: requirement.notes || "",
      is_addressed: requirement.is_addressed,
      page_reference: requirement.page_reference ? String(requirement.page_reference) : "",
      keywords: requirement.keywords?.join(", ") || "",
    });
    // If already addressed, fetch the generated content
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

    try {
      const result = await draftApi.generateSection(requirement.id);

      // Poll for completion
      let completed = false;
      while (!completed) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        const status = await draftApi.getGenerationStatus(result.task_id);

        if (status.status === "completed") {
          completed = true;
          // Refresh the matrix to get updated content
          const matrixData = await analysisApi.getComplianceMatrix(rfpId);
          if (matrixData && matrixData.requirements) {
            setRequirements(matrixData.requirements);
            // Find and set the generated content
            const updated = matrixData.requirements.find((r: ComplianceRequirement) => r.id === requirement.id);
            if (updated?.generated_content) {
              setGeneratedContent(updated.generated_content as GeneratedContent);
            }
          }
        } else if (status.status === "failed") {
          completed = true;
          setError("Generation failed. Please try again.");
        }
      }
    } catch (err) {
      console.error("Generation failed:", err);
      setError("Failed to generate content. Please try again.");
    } finally {
      setIsGenerating(false);
      setGeneratingId(undefined);
    }
  };

  const handleRegenerate = () => {
    if (selectedRequirement) {
      handleGenerate(selectedRequirement);
    }
  };

  const handleApprove = async () => {
    if (!selectedRequirement) return;
    try {
      const updated = await analysisApi.updateRequirement(rfpId, selectedRequirement.id, {
        is_addressed: true,
      });
      setRequirements(updated.requirements);
    } catch (err) {
      console.error("Failed to update requirement", err);
      setError("Failed to update requirement status.");
    }
  };

  const handleEditRequirement = () => {
    if (!selectedRequirement) return;
    setIsEditingRequirement(true);
  };

  const handleSaveRequirement = async () => {
    if (!selectedRequirement) return;
    try {
      setIsSavingRequirement(true);
      const payload = {
        section: editForm.section,
        requirement_text: editForm.requirement_text,
        importance: editForm.importance as ComplianceRequirement["importance"],
        category: editForm.category || null,
        notes: editForm.notes || null,
        is_addressed: editForm.is_addressed,
        page_reference: editForm.page_reference
          ? parseInt(editForm.page_reference, 10)
          : undefined,
        keywords: editForm.keywords
          ? editForm.keywords.split(",").map((k) => k.trim()).filter(Boolean)
          : [],
      };
      const updated = await analysisApi.updateRequirement(
        rfpId,
        selectedRequirement.id,
        payload
      );
      setRequirements(updated.requirements);
      const refreshed = updated.requirements.find(
        (req) => req.id === selectedRequirement.id
      );
      if (refreshed) {
        setSelectedRequirement(refreshed);
      }
      setIsEditingRequirement(false);
    } catch (err) {
      console.error("Failed to save requirement", err);
      setError("Failed to save requirement changes.");
    } finally {
      setIsSavingRequirement(false);
    }
  };

  const handleDeleteRequirement = async () => {
    if (!selectedRequirement) return;
    try {
      await analysisApi.deleteRequirement(rfpId, selectedRequirement.id);
      setRequirements((prev) =>
        prev.filter((req) => req.id !== selectedRequirement.id)
      );
      setSelectedRequirement(undefined);
      setIsEditingRequirement(false);
    } catch (err) {
      console.error("Failed to delete requirement", err);
      setError("Failed to delete requirement.");
    }
  };

  const handleCreateRequirement = async () => {
    try {
      setIsSavingRequirement(true);
      const payload = {
        section: newRequirement.section,
        requirement_text: newRequirement.requirement_text,
        importance: newRequirement.importance as ComplianceRequirement["importance"],
        category: newRequirement.category || null,
        notes: newRequirement.notes || null,
        page_reference: newRequirement.page_reference
          ? parseInt(newRequirement.page_reference, 10)
          : undefined,
        keywords: newRequirement.keywords
          ? newRequirement.keywords.split(",").map((k) => k.trim()).filter(Boolean)
          : [],
      };
      const updated = await analysisApi.addRequirement(rfpId, payload);
      setRequirements(updated.requirements);
      setShowCreateRequirement(false);
      setNewRequirement({
        section: "",
        requirement_text: "",
        importance: "mandatory",
        category: "",
        notes: "",
        page_reference: "",
        keywords: "",
      });
    } catch (err) {
      console.error("Failed to create requirement", err);
      setError("Failed to add requirement.");
    } finally {
      setIsSavingRequirement(false);
    }
  };

  const handleExport = async (format: "docx" | "pdf") => {
    if (!rfp) return;

    try {
      setIsExporting(true);
      const blob = format === "docx"
        ? await exportApi.exportProposalDocx(rfp.id)
        : await exportApi.exportProposalPdf(rfp.id);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `proposal_${rfp.solicitation_number || rfp.id}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Export failed:", err);
      setError("Failed to export proposal. Please try again.");
    } finally {
      setIsExporting(false);
    }
  };

  // Calculate stats
  const stats = {
    addressed: requirements.filter(r => r.is_addressed).length,
    total: requirements.length,
    mandatory: requirements.filter(r => r.importance === "mandatory").length,
    mandatoryAddressed: requirements.filter(
      r => r.importance === "mandatory" && r.is_addressed
    ).length,
  };
  const completionPercent = stats.total > 0 ? (stats.addressed / stats.total) * 100 : 0;

  // Group requirements for shred view
  const groupedRequirements = requirements.reduce((acc, req) => {
    const category = req.category || "Other";
    if (!acc[category]) acc[category] = [];
    acc[category].push(req);
    return acc;
  }, {} as Record<string, ComplianceRequirement[]>);

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

  if (error || !rfp) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Error" description="Unable to load RFP" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
            <p className="text-destructive mb-4">{error || "RFP not found"}</p>
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
      {/* Header */}
      <Header
        title={rfp.title}
        description={`${rfp.solicitation_number || rfp.notice_id} • ${rfp.agency}`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" asChild>
              <Link href="/opportunities">
                <ArrowLeft className="w-4 h-4" />
                Back
              </Link>
            </Button>
            <div className="flex items-center border border-border rounded-lg">
              <Button
                variant={viewMode === "list" ? "default" : "ghost"}
                size="sm"
                onClick={() => setViewMode("list")}
                className="rounded-r-none"
              >
                <List className="w-4 h-4" />
              </Button>
              <Button
                variant={viewMode === "shred" ? "default" : "ghost"}
                size="sm"
                onClick={() => setViewMode("shred")}
                className="rounded-l-none"
              >
                <Grid3X3 className="w-4 h-4" />
              </Button>
            </div>
            <Button
              variant="outline"
              onClick={() => setShowCreateRequirement(true)}
            >
              <Plus className="w-4 h-4" />
              Add Requirement
            </Button>
            <Button
              variant="outline"
              onClick={() => handleExport("docx")}
              disabled={isExporting}
            >
              {isExporting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              Export
            </Button>
          </div>
        }
      />

      {/* Status Bar */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-border bg-card/30">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            {rfp.is_qualified ? (
              <CheckCircle2 className="w-5 h-5 text-accent" />
            ) : (
              <AlertCircle className="w-5 h-5 text-warning" />
            )}
            <span className="text-sm font-medium">
              {rfp.is_qualified
                ? `Qualified (${rfp.qualification_score}% match)`
                : "Pending Qualification"}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {rfp.set_aside && <Badge variant="outline">{rfp.set_aside}</Badge>}
            {rfp.naics_code && <Badge variant="outline">NAICS {rfp.naics_code}</Badge>}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Proposal Completion</p>
            <p className="text-sm font-medium">
              {stats.addressed}/{stats.total} requirements
            </p>
          </div>
          <div className="w-32">
            <Progress value={completionPercent} />
          </div>
        </div>
      </div>

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
                    Comparing snapshots {snapshotDiff.from_snapshot_id} → {snapshotDiff.to_snapshot_id}
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
                      <p className="text-foreground">{change.before || "—"}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">After</p>
                      <p className="text-foreground">{change.after || "—"}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {isEditingRequirement && selectedRequirement && (
        <div className="px-6 pt-4">
          <Card className="border border-border">
            <CardContent className="p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    Edit Requirement {selectedRequirement.id}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Update compliance metadata and notes
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setIsEditingRequirement(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={handleDeleteRequirement}
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </Button>
                  <Button onClick={handleSaveRequirement} disabled={isSavingRequirement}>
                    <Pencil className="w-4 h-4" />
                    Save
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground">Section</label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={editForm.section}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, section: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Importance</label>
                  <select
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={editForm.importance}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, importance: e.target.value }))
                    }
                  >
                    <option value="mandatory">Mandatory</option>
                    <option value="evaluated">Evaluated</option>
                    <option value="optional">Optional</option>
                    <option value="informational">Informational</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Category</label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={editForm.category}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, category: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Page Reference</label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={editForm.page_reference}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        page_reference: e.target.value,
                      }))
                    }
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="text-xs text-muted-foreground">Requirement Text</label>
                  <textarea
                    className="mt-1 w-full min-h-[120px] rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={editForm.requirement_text}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        requirement_text: e.target.value,
                      }))
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Keywords (comma separated)</label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={editForm.keywords}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, keywords: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Notes</label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={editForm.notes}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, notes: e.target.value }))
                    }
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editForm.is_addressed}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        is_addressed: e.target.checked,
                      }))
                    }
                  />
                  <span className="text-sm text-muted-foreground">
                    Mark as addressed
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {showCreateRequirement && (
        <div className="px-6 pt-4">
          <Card className="border border-border">
            <CardContent className="p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    Add Requirement
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Insert a new requirement into the matrix
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setShowCreateRequirement(false)}
                  >
                    Cancel
                  </Button>
                  <Button onClick={handleCreateRequirement} disabled={isSavingRequirement}>
                    <Plus className="w-4 h-4" />
                    Add
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground">Section</label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={newRequirement.section}
                    onChange={(e) =>
                      setNewRequirement((prev) => ({ ...prev, section: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Importance</label>
                  <select
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={newRequirement.importance}
                    onChange={(e) =>
                      setNewRequirement((prev) => ({ ...prev, importance: e.target.value }))
                    }
                  >
                    <option value="mandatory">Mandatory</option>
                    <option value="evaluated">Evaluated</option>
                    <option value="optional">Optional</option>
                    <option value="informational">Informational</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Category</label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={newRequirement.category}
                    onChange={(e) =>
                      setNewRequirement((prev) => ({ ...prev, category: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Page Reference</label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={newRequirement.page_reference}
                    onChange={(e) =>
                      setNewRequirement((prev) => ({
                        ...prev,
                        page_reference: e.target.value,
                      }))
                    }
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="text-xs text-muted-foreground">Requirement Text</label>
                  <textarea
                    className="mt-1 w-full min-h-[120px] rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={newRequirement.requirement_text}
                    onChange={(e) =>
                      setNewRequirement((prev) => ({
                        ...prev,
                        requirement_text: e.target.value,
                      }))
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Keywords (comma separated)</label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={newRequirement.keywords}
                    onChange={(e) =>
                      setNewRequirement((prev) => ({ ...prev, keywords: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Notes</label>
                  <input
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={newRequirement.notes}
                    onChange={(e) =>
                      setNewRequirement((prev) => ({ ...prev, notes: e.target.value }))
                    }
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Content - Different views */}
      {viewMode === "list" ? (
        /* Split Screen View */
        <div className="flex-1 flex overflow-hidden">
          {/* Left Panel - Compliance Matrix */}
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

          {/* Right Panel - Draft Preview */}
          <div className="w-1/2">
            <DraftPreview
              requirement={selectedRequirement}
              generatedContent={generatedContent}
              isGenerating={isGenerating}
              onRegenerate={handleRegenerate}
              onApprove={handleApprove}
              onEdit={handleEditRequirement}
            />
          </div>
        </div>
      ) : (
        /* Shred View - Categorized Requirements */
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-6xl mx-auto space-y-8">
            {Object.entries(groupedRequirements).map(([category, reqs]) => (
              <div key={category}>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">{category}</h2>
                  <Badge variant="outline">
                    {reqs.filter(r => r.is_addressed).length}/{reqs.length} addressed
                  </Badge>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {reqs.map((req) => (
                    <div
                      key={req.id}
                      className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                        req.is_addressed
                          ? "border-accent/30 bg-accent/5"
                          : "border-border hover:border-primary/30"
                      }`}
                      onClick={() => {
                        handleSelectRequirement(req);
                        setViewMode("list");
                      }}
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <Badge
                          variant={
                            req.importance === "mandatory"
                              ? "destructive"
                              : req.importance === "evaluated"
                              ? "default"
                              : "secondary"
                          }
                          className="text-xs"
                        >
                          {req.importance}
                        </Badge>
                        <span className="text-xs text-muted-foreground font-mono">
                          {req.section}
                        </span>
                      </div>

                      <p className="text-sm line-clamp-3 mb-3">
                        {req.requirement_text}
                      </p>

                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1">
                          {req.is_addressed ? (
                            <>
                              <CheckCircle2 className="w-4 h-4 text-accent" />
                              <span className="text-xs text-accent">Addressed</span>
                            </>
                          ) : (
                            <>
                              <FileText className="w-4 h-4 text-muted-foreground" />
                              <span className="text-xs text-muted-foreground">Pending</span>
                            </>
                          )}
                        </div>

                        {!req.is_addressed && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleGenerate(req);
                            }}
                            disabled={isGenerating && generatingId === req.id}
                          >
                            {isGenerating && generatingId === req.id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              "Generate"
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
