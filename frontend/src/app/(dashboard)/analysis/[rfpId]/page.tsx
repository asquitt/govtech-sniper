"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Download,
  Share2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileText,
  List,
  Grid3X3,
} from "lucide-react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
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
    // Mark requirement as addressed in local state
    setRequirements(prev =>
      prev.map(r =>
        r.id === selectedRequirement.id ? { ...r, is_addressed: true } : r
      )
    );
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
              onEdit={() => console.log("Edit")}
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
