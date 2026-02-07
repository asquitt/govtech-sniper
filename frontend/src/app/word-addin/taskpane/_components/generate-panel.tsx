"use client";

import React, { useState, useRef, useEffect } from "react";
import { Loader2, Sparkles, FileDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { draftApi } from "@/lib/api/draft";
import {
  insertSectionContent,
  OfficeNotAvailableError,
} from "@/lib/office/word-document";
import type { ProposalSection } from "@/types";

interface GeneratePanelProps {
  section: ProposalSection | null;
  isInOffice: boolean;
}

export function GeneratePanel({ section, isInOffice }: GeneratePanelProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [isInserting, setIsInserting] = useState(false);
  const [generatedContent, setGeneratedContent] = useState<string | null>(null);
  const [wordCount, setWordCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  if (!section) {
    return (
      <p className="text-xs text-muted-foreground py-4 text-center">
        Select a section from the Sections tab to generate content.
      </p>
    );
  }

  const handleGenerate = async () => {
    if (!section.requirement_id) {
      setError("Section has no requirement ID — cannot generate.");
      return;
    }

    setIsGenerating(true);
    setError(null);
    setGeneratedContent(null);
    setWordCount(null);

    try {
      const { task_id } = await draftApi.generateSection(
        section.requirement_id,
        {
          requirement_id: section.requirement_id,
          max_words: 500,
          tone: "professional",
          include_citations: true,
        }
      );

      // Poll for completion
      pollRef.current = setInterval(async () => {
        try {
          const status = await draftApi.getGenerationStatus(task_id);
          if (status.status === "completed") {
            if (pollRef.current) clearInterval(pollRef.current);
            // Fetch updated section to get generated content
            const updated = await draftApi.getSection(section.id);
            const content =
              updated.generated_content?.clean_text ||
              updated.final_content ||
              "";
            setGeneratedContent(content);
            setWordCount(
              content.split(/\s+/).filter((w: string) => w.length > 0).length
            );
            setIsGenerating(false);
          } else if (status.status === "failed") {
            if (pollRef.current) clearInterval(pollRef.current);
            setError(
              typeof status.error === "string"
                ? status.error
                : "Generation failed"
            );
            setIsGenerating(false);
          }
        } catch {
          if (pollRef.current) clearInterval(pollRef.current);
          setError("Failed to check generation status");
          setIsGenerating(false);
        }
      }, 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
      setIsGenerating(false);
    }
  };

  const handleInsert = async () => {
    if (!generatedContent) return;
    setIsInserting(true);
    try {
      await insertSectionContent(
        `${section.section_number}: ${section.title}`,
        generatedContent
      );
    } catch (err) {
      if (err instanceof OfficeNotAvailableError) {
        setError("Open in Word to insert content.");
      } else {
        setError(err instanceof Error ? err.message : "Insert failed");
      }
    } finally {
      setIsInserting(false);
    }
  };

  return (
    <div className="space-y-3">
      {/* Section info */}
      <div className="rounded-md border border-border bg-card/50 p-2 space-y-1">
        <p className="text-xs font-medium">
          {section.section_number}: {section.title}
        </p>
        {section.requirement_text && (
          <p className="text-[10px] text-muted-foreground line-clamp-3">
            {section.requirement_text}
          </p>
        )}
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          <span>Status: {section.status}</span>
          {section.word_count && <span>{section.word_count} words</span>}
        </div>
      </div>

      {/* Generate button */}
      <Button
        size="sm"
        className="w-full text-xs"
        onClick={handleGenerate}
        disabled={isGenerating || !section.requirement_id}
      >
        {isGenerating ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : (
          <Sparkles className="w-3 h-3" />
        )}
        {isGenerating ? "Generating..." : "Generate Content"}
      </Button>

      {!section.requirement_id && (
        <p className="text-[10px] text-muted-foreground text-center">
          This section has no linked requirement. Add a requirement ID to enable
          generation.
        </p>
      )}

      {/* Error */}
      {error && (
        <p className="text-[11px] text-red-500 bg-red-500/10 border border-red-500/30 rounded-md px-2 py-1.5">
          {error}
        </p>
      )}

      {/* Generated content preview */}
      {generatedContent && (
        <div className="space-y-2">
          {wordCount !== null && (
            <p className="text-[10px] text-muted-foreground">
              {wordCount} words generated
            </p>
          )}
          <div className="rounded-md border border-primary/30 bg-primary/5 p-2">
            <p className="text-[11px] line-clamp-8">{generatedContent}</p>
          </div>
          <Button
            size="sm"
            className="w-full text-xs"
            onClick={handleInsert}
            disabled={!isInOffice || isInserting}
          >
            {isInserting ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <FileDown className="w-3 h-3" />
            )}
            Insert into Word
          </Button>
        </div>
      )}
    </div>
  );
}
