"use client";

import React, { useState } from "react";
import { CheckCircle2, Loader2, Maximize2, RefreshCw, Save } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { WritingPlanPanel } from "@/components/proposals/writing-plan-panel";
import { RichTextEditor } from "@/components/proposals/rich-text-editor";
import type { ProposalSection } from "@/types";
import { draftApi } from "@/lib/api";
import { wrapInSuggestionMarks } from "@/components/proposals/track-changes-extension";

interface SectionEditorProps {
  selectedSection: ProposalSection | null;
  editorContent: string;
  onEditorContentChange: (content: string) => void;
  writingPlan: string;
  onWritingPlanChange: (plan: string) => void;
  onSaveWritingPlan: () => void;
  isSavingPlan: boolean;
  onSave: () => void;
  onApprove: () => void;
  isSaving: boolean;
  onSectionUpdate?: (section: ProposalSection) => void;
}

function QualityBadge({ score }: { score: number | undefined }) {
  if (score == null) return null;
  const rounded = Math.round(score);
  const color =
    rounded >= 85
      ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
      : rounded >= 70
        ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
        : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${color}`}>
      Q: {rounded}
    </span>
  );
}

const TONE_OPTIONS = ["professional", "technical", "executive"] as const;

export function SectionEditor({
  selectedSection,
  editorContent,
  onEditorContentChange,
  writingPlan,
  onWritingPlanChange,
  onSaveWritingPlan,
  isSavingPlan,
  onSave,
  onApprove,
  isSaving,
  onSectionUpdate,
}: SectionEditorProps) {
  const [isRewriting, setIsRewriting] = useState(false);
  const [isExpanding, setIsExpanding] = useState(false);
  const [showToneMenu, setShowToneMenu] = useState(false);

  const hasContent = Boolean(
    selectedSection?.final_content || selectedSection?.generated_content
  );

  const handleRewrite = async (tone: string) => {
    if (!selectedSection) return;
    setShowToneMenu(false);
    setIsRewriting(true);
    try {
      const updated = await draftApi.rewriteSection(selectedSection.id, { tone });
      if (updated.generated_content) {
        onEditorContentChange(wrapInSuggestionMarks(updated.generated_content.clean_text));
      }
      onSectionUpdate?.(updated);
    } catch (err) {
      console.error("Rewrite failed", err);
    } finally {
      setIsRewriting(false);
    }
  };

  const handleExpand = async () => {
    if (!selectedSection) return;
    setIsExpanding(true);
    try {
      const targetWords = (selectedSection.word_count || 300) * 2;
      const updated = await draftApi.expandSection(selectedSection.id, {
        target_words: Math.min(targetWords, 3000),
      });
      if (updated.generated_content) {
        onEditorContentChange(wrapInSuggestionMarks(updated.generated_content.clean_text));
      }
      onSectionUpdate?.(updated);
    } catch (err) {
      console.error("Expand failed", err);
    } finally {
      setIsExpanding(false);
    }
  };

  const aiLoading = isRewriting || isExpanding;

  return (
    <Card className="border border-border h-full flex flex-col">
      <CardContent className="p-4 flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div>
              <p className="text-sm font-semibold text-foreground">
                {selectedSection ? selectedSection.title : "Select a Section"}
              </p>
              {selectedSection && (
                <p className="text-xs text-muted-foreground">
                  {selectedSection.section_number}
                </p>
              )}
            </div>
            <QualityBadge score={selectedSection?.quality_score} />
          </div>
          <div className="flex items-center gap-1.5">
            {/* Rewrite dropdown */}
            <div className="relative">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowToneMenu(!showToneMenu)}
                disabled={!selectedSection || !hasContent || aiLoading}
              >
                {isRewriting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="w-3.5 h-3.5" />
                )}
                Rewrite
              </Button>
              {showToneMenu && (
                <div className="absolute right-0 top-full mt-1 z-10 bg-popover border border-border rounded-md shadow-md py-1 min-w-[140px]">
                  {TONE_OPTIONS.map((tone) => (
                    <button
                      key={tone}
                      className="w-full px-3 py-1.5 text-sm text-left hover:bg-accent capitalize"
                      onClick={() => handleRewrite(tone)}
                    >
                      {tone}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {/* Expand */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleExpand}
              disabled={!selectedSection || !hasContent || aiLoading}
            >
              {isExpanding ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Maximize2 className="w-3.5 h-3.5" />
              )}
              Expand
            </Button>
            <Button variant="outline" size="sm" onClick={onApprove} disabled={!selectedSection}>
              <CheckCircle2 className="w-3.5 h-3.5" />
              Approve
            </Button>
            <Button size="sm" onClick={onSave} disabled={!selectedSection || isSaving}>
              <Save className="w-3.5 h-3.5" />
              Save
            </Button>
          </div>
        </div>
        {selectedSection && (
          <WritingPlanPanel
            writingPlan={writingPlan}
            onChange={onWritingPlanChange}
            onSave={onSaveWritingPlan}
            isSaving={isSavingPlan}
            disabled={!selectedSection}
          />
        )}
        <RichTextEditor
          content={editorContent}
          onUpdate={onEditorContentChange}
          onAutoSave={selectedSection ? async (html) => {
            try {
              await draftApi.updateSection(selectedSection.id, {
                final_content: html,
              });
            } catch (err) {
              console.error("Auto-save failed", err);
            }
          } : undefined}
          disabled={!selectedSection || aiLoading}
        />
      </CardContent>
    </Card>
  );
}
