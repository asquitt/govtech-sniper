"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { draftApi } from "@/lib/api";
import type { ProposalOutline, OutlineSection } from "@/types";

interface OutlineViewProps {
  proposalId: number;
  onApproved?: () => void;
}

function OutlineSectionCard({
  section,
  proposalId,
  onDelete,
}: {
  section: OutlineSection;
  proposalId: number;
  onDelete: (id: number) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasChildren = section.children && section.children.length > 0;

  return (
    <div className="space-y-1">
      <div className="flex items-start gap-2 px-2 py-1.5 rounded hover:bg-secondary/50 group">
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-0.5 flex-shrink-0"
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-4 h-4 text-muted-foreground" />
            )
          ) : (
            <FileText className="w-4 h-4 text-muted-foreground" />
          )}
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground">{section.title}</p>
          {section.description && (
            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
              {section.description}
            </p>
          )}
          <div className="flex items-center gap-2 mt-1">
            {section.mapped_requirement_ids.length > 0 && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                {section.mapped_requirement_ids.length} req
              </Badge>
            )}
            {section.estimated_pages && (
              <span className="text-[10px] text-muted-foreground">
                ~{section.estimated_pages}p
              </span>
            )}
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="opacity-0 group-hover:opacity-100 flex-shrink-0"
          onClick={() => onDelete(section.id)}
        >
          <Trash2 className="w-3 h-3" />
        </Button>
      </div>
      {hasChildren && isExpanded && (
        <div className="ml-6 border-l border-border pl-2 space-y-1">
          {section.children.map((child) => (
            <OutlineSectionCard
              key={child.id}
              section={child}
              proposalId={proposalId}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function OutlineView({ proposalId, onApproved }: OutlineViewProps) {
  const [outline, setOutline] = useState<ProposalOutline | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOutline = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await draftApi.getOutline(proposalId);
      setOutline(data);
    } catch {
      setOutline(null);
    } finally {
      setIsLoading(false);
    }
  }, [proposalId]);

  useEffect(() => {
    loadOutline();
  }, [loadOutline]);

  const handleGenerate = async () => {
    try {
      setIsGenerating(true);
      setError(null);
      await draftApi.generateOutline(proposalId);
      // Poll for completion
      const poll = setInterval(async () => {
        try {
          const data = await draftApi.getOutline(proposalId);
          if (data.status !== "generating") {
            clearInterval(poll);
            setOutline(data);
            setIsGenerating(false);
          }
        } catch {
          // Still generating, keep polling
        }
      }, 3000);
      // Safety timeout
      setTimeout(() => {
        clearInterval(poll);
        setIsGenerating(false);
        loadOutline();
      }, 60000);
    } catch (err) {
      console.error("Failed to generate outline", err);
      setError("Failed to generate outline.");
      setIsGenerating(false);
    }
  };

  const handleDelete = async (sectionId: number) => {
    try {
      await draftApi.deleteOutlineSection(proposalId, sectionId);
      loadOutline();
    } catch (err) {
      console.error("Failed to delete section", err);
    }
  };

  const handleApprove = async () => {
    try {
      setIsApproving(true);
      const result = await draftApi.approveOutline(proposalId);
      setOutline((prev) =>
        prev ? { ...prev, status: "approved" } : null
      );
      onApproved?.();
    } catch (err) {
      console.error("Failed to approve outline", err);
      setError("Failed to approve outline.");
    } finally {
      setIsApproving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!outline) {
    return (
      <Card className="border border-border">
        <CardContent className="p-6 text-center space-y-3">
          <Sparkles className="w-8 h-8 text-primary mx-auto" />
          <p className="text-sm text-foreground font-medium">No outline yet</p>
          <p className="text-xs text-muted-foreground">
            Generate a structured outline from your compliance matrix.
          </p>
          <Button onClick={handleGenerate} disabled={isGenerating}>
            {isGenerating ? (
              <Loader2 className="w-4 h-4 animate-spin mr-1" />
            ) : (
              <Sparkles className="w-4 h-4 mr-1" />
            )}
            Generate Outline
          </Button>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-foreground">Proposal Outline</p>
            <p className="text-xs text-muted-foreground">
              {outline.sections.length} top-level sections
              {outline.status === "approved" && " (Approved)"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerate}
              disabled={isGenerating}
            >
              {isGenerating ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Sparkles className="w-3 h-3" />
              )}
              Regenerate
            </Button>
            {outline.status !== "approved" && (
              <Button size="sm" onClick={handleApprove} disabled={isApproving}>
                {isApproving ? (
                  <Loader2 className="w-3 h-3 animate-spin mr-1" />
                ) : (
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                )}
                Approve
              </Button>
            )}
          </div>
        </div>

        <div className="space-y-1 max-h-96 overflow-y-auto">
          {outline.sections.map((section) => (
            <OutlineSectionCard
              key={section.id}
              section={section}
              proposalId={proposalId}
              onDelete={handleDelete}
            />
          ))}
        </div>

        {error && <p className="text-xs text-destructive">{error}</p>}
      </CardContent>
    </Card>
  );
}
