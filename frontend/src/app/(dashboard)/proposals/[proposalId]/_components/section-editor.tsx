"use client";

import React from "react";
import { CheckCircle2, Save } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { WritingPlanPanel } from "@/components/proposals/writing-plan-panel";
import { RichTextEditor } from "@/components/proposals/rich-text-editor";
import type { ProposalSection } from "@/types";
import { draftApi } from "@/lib/api";

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
}

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
}: SectionEditorProps) {
  return (
    <Card className="border border-border h-full flex flex-col">
      <CardContent className="p-4 flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-4">
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
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={onApprove} disabled={!selectedSection}>
              <CheckCircle2 className="w-4 h-4" />
              Approve
            </Button>
            <Button onClick={onSave} disabled={!selectedSection || isSaving}>
              <Save className="w-4 h-4" />
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
          disabled={!selectedSection}
        />
      </CardContent>
    </Card>
  );
}
