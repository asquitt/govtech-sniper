"use client";

import React from "react";
import { FileText, ExternalLink } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { parseCitations, type ParsedCitation } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface CitationViewerProps {
  text: string;
  className?: string;
  onCitationClick?: (citation: ParsedCitation) => void;
}

/**
 * CitationViewer Component
 * 
 * Renders text with embedded citations. Detects [[Source: filename, Page X]] patterns
 * and renders them as interactive tooltips.
 */
export function CitationViewer({
  text,
  className,
  onCitationClick,
}: CitationViewerProps) {
  const citations = parseCitations(text);
  
  if (citations.length === 0) {
    return <p className={cn("text-foreground leading-relaxed", className)}>{text}</p>;
  }

  // Build segments with text and citations interleaved
  const segments: React.ReactNode[] = [];
  let lastIndex = 0;

  citations.forEach((citation, index) => {
    // Add text before this citation
    if (citation.startIndex > lastIndex) {
      segments.push(
        <span key={`text-${index}`}>
          {text.slice(lastIndex, citation.startIndex)}
        </span>
      );
    }

    // Add the citation as an interactive element
    segments.push(
      <CitationMark
        key={`citation-${index}`}
        citation={citation}
        onClick={() => onCitationClick?.(citation)}
      />
    );

    lastIndex = citation.endIndex;
  });

  // Add any remaining text after the last citation
  if (lastIndex < text.length) {
    segments.push(<span key="text-end">{text.slice(lastIndex)}</span>);
  }

  return (
    <p className={cn("text-foreground leading-relaxed", className)}>
      {segments}
    </p>
  );
}

interface CitationMarkProps {
  citation: ParsedCitation;
  onClick?: () => void;
}

function CitationMark({ citation, onClick }: CitationMarkProps) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={onClick}
            className="citation-mark"
            type="button"
          >
            <FileText className="w-3 h-3" />
            <span className="max-w-[120px] truncate">{citation.sourceFile}</span>
            {citation.pageNumber && (
              <span className="text-accent/70">p.{citation.pageNumber}</span>
            )}
          </button>
        </TooltipTrigger>
        <TooltipContent className="max-w-sm p-3">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-accent" />
              <span className="font-medium text-foreground">
                Verified Source
              </span>
            </div>
            <div className="text-sm text-muted-foreground">
              <p>
                <strong>File:</strong> {citation.sourceFile}
              </p>
              {citation.pageNumber && (
                <p>
                  <strong>Page:</strong> {citation.pageNumber}
                </p>
              )}
            </div>
            <div className="flex items-center gap-1 text-xs text-accent">
              <ExternalLink className="w-3 h-3" />
              Click to view source document
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * CitationSummary Component
 * 
 * Shows a summary of all citations in a text block.
 */
interface CitationSummaryProps {
  text: string;
  className?: string;
}

export function CitationSummary({ text, className }: CitationSummaryProps) {
  const citations = parseCitations(text);

  if (citations.length === 0) {
    return null;
  }

  // Group citations by source file
  const grouped = citations.reduce((acc, citation) => {
    const key = citation.sourceFile;
    if (!acc[key]) {
      acc[key] = [];
    }
    if (citation.pageNumber && !acc[key].includes(citation.pageNumber)) {
      acc[key].push(citation.pageNumber);
    }
    return acc;
  }, {} as Record<string, number[]>);

  return (
    <div className={cn("space-y-2", className)}>
      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        Sources ({citations.length})
      </h4>
      <div className="space-y-1">
        {Object.entries(grouped).map(([file, pages]) => (
          <div
            key={file}
            className="flex items-center justify-between p-2 rounded-lg bg-secondary/50 text-sm"
          >
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-accent" />
              <span className="font-medium truncate max-w-[180px]">{file}</span>
            </div>
            {pages.length > 0 && (
              <span className="text-xs text-muted-foreground">
                Pages: {pages.sort((a, b) => a - b).join(", ")}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * CitationHighlight Component
 * 
 * A simpler version that just highlights citations without tooltips.
 */
interface CitationHighlightProps {
  text: string;
  className?: string;
}

export function CitationHighlight({ text, className }: CitationHighlightProps) {
  // Replace citation patterns with highlighted spans
  const highlighted = text.replace(
    /\[\[Source:\s*([^,\]]+)(?:,\s*[Pp]age\s*(\d+))?\]\]/g,
    (_, file, page) => {
      const pageText = page ? `, p.${page}` : "";
      return `<cite class="citation-mark inline-flex gap-1"><span>${file}${pageText}</span></cite>`;
    }
  );

  return (
    <p
      className={cn("text-foreground leading-relaxed", className)}
      dangerouslySetInnerHTML={{ __html: highlighted }}
    />
  );
}

