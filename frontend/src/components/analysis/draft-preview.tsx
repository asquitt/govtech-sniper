"use client";

import React from "react";
import {
  Copy,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
  Edit3,
  Loader2,
  FileText,
  Sparkles,
  Clock,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CitationViewer, CitationSummary } from "./citation-viewer";
import { cn } from "@/lib/utils";
import type { ComplianceRequirement, GeneratedContent } from "@/types";

interface DraftPreviewProps {
  requirement?: ComplianceRequirement;
  generatedContent?: GeneratedContent;
  isGenerating?: boolean;
  onRegenerate?: () => void;
  onApprove?: () => void;
  onEdit?: () => void;
}

export function DraftPreview({
  requirement,
  generatedContent,
  isGenerating,
  onRegenerate,
  onApprove,
  onEdit,
}: DraftPreviewProps) {
  const copyToClipboard = () => {
    if (generatedContent) {
      navigator.clipboard.writeText(generatedContent.raw_text);
    }
  };

  // Empty state - no requirement selected
  if (!requirement) {
    return (
      <div className="split-panel">
        <div className="split-panel-header">
          <h2 className="font-semibold text-foreground">Draft Preview</h2>
        </div>
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center max-w-sm">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <FileText className="w-8 h-8 text-primary/50" />
            </div>
            <h3 className="font-medium text-foreground mb-2">
              Select a Requirement
            </h3>
            <p className="text-sm text-muted-foreground">
              Choose a requirement from the compliance matrix to generate an
              AI-powered response.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="split-panel">
      {/* Header */}
      <div className="split-panel-header">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-foreground">Draft Preview</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {requirement.section} • {requirement.category || "General"}
            </p>
          </div>
          {(generatedContent || onEdit) && (
            <div className="flex items-center gap-2">
              {generatedContent && (
                <>
                  <Button variant="ghost" size="sm" onClick={copyToClipboard}>
                    <Copy className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={onRegenerate}>
                    <RefreshCw className="w-4 h-4" />
                  </Button>
                </>
              )}
              {onEdit && (
                <Button variant="ghost" size="sm" onClick={onEdit}>
                  <Edit3 className="w-4 h-4" />
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      <ScrollArea className="split-panel-content">
        <div className="p-4 space-y-6">
          {/* Requirement Section */}
          <div className="p-4 rounded-lg bg-secondary/50 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="text-xs">
                Requirement
              </Badge>
              <span className="text-xs text-muted-foreground font-mono">
                {requirement.id}
              </span>
            </div>
            <p className="text-sm text-foreground leading-relaxed">
              {requirement.requirement_text}
            </p>
          </div>

          {/* Loading State */}
          {isGenerating && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="relative">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                  <Sparkles className="w-8 h-8 text-primary animate-pulse" />
                </div>
                <div className="absolute -inset-2 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
              </div>
              <p className="mt-4 text-sm font-medium text-foreground">
                Generating response...
              </p>
              <p className="text-xs text-muted-foreground">
                AI is writing with citations from your Knowledge Base
              </p>
            </div>
          )}

          {/* Generated Content */}
          {generatedContent && !isGenerating && (
            <>
              {/* Response */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <span className="text-sm font-medium text-foreground">
                    AI-Generated Response
                  </span>
                </div>
                <div className="p-4 rounded-lg border border-primary/20 bg-primary/5">
                  <CitationViewer
                    text={generatedContent.raw_text}
                    className="text-sm"
                  />
                </div>
              </div>

              {/* Citations Summary */}
              <CitationSummary text={generatedContent.raw_text} />

              {/* Metadata */}
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {generatedContent.generation_time_seconds.toFixed(1)}s
                </div>
                <div className="flex items-center gap-1">
                  <Zap className="w-3 h-3" />
                  {generatedContent.tokens_used.toLocaleString()} tokens
                </div>
                <span>{generatedContent.model_used}</span>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 pt-4 border-t border-border">
                <Button onClick={onApprove} className="flex-1">
                  <ThumbsUp className="w-4 h-4" />
                  Approve & Add to Proposal
                </Button>
                <Button variant="outline" onClick={onRegenerate}>
                  <RefreshCw className="w-4 h-4" />
                  Regenerate
                </Button>
              </div>
            </>
          )}

          {/* Not yet generated */}
          {!generatedContent && !isGenerating && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center mb-3">
                <Sparkles className="w-6 h-6 text-accent" />
              </div>
              <p className="text-sm text-muted-foreground">
                Click &ldquo;Generate&rdquo; to create an AI response with citations
              </p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
