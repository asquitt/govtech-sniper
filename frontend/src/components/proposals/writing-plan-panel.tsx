"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight, Save, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface WritingPlanPanelProps {
  writingPlan: string;
  onChange: (plan: string) => void;
  onSave: () => void;
  isSaving?: boolean;
  disabled?: boolean;
}

export function WritingPlanPanel({
  writingPlan,
  onChange,
  onSave,
  isSaving = false,
  disabled = false,
}: WritingPlanPanelProps) {
  const [isExpanded, setIsExpanded] = useState(!!writingPlan);

  return (
    <div className="border border-border rounded-lg bg-card">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-foreground hover:bg-secondary/50 rounded-t-lg transition-colors"
      >
        <span>Writing Plan</span>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
        )}
      </button>
      <div
        className={cn(
          "overflow-hidden transition-all duration-200",
          isExpanded ? "max-h-96" : "max-h-0"
        )}
      >
        <div className="px-3 pb-3 space-y-2">
          <p className="text-xs text-muted-foreground">
            Add bullet points, key themes, or tone guidance to steer AI generation.
          </p>
          <textarea
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm min-h-[100px] resize-y"
            placeholder={`- Highlight 10+ years of Agile experience\n- Emphasize CMMI Level 3 certification\n- Use confident, authoritative tone\n- Reference the DARPA project as past performance`}
            value={writingPlan}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
          />
          <Button
            size="sm"
            variant="outline"
            className="w-full"
            onClick={onSave}
            disabled={disabled || isSaving}
          >
            {isSaving ? (
              <Loader2 className="w-3 h-3 animate-spin mr-1" />
            ) : (
              <Save className="w-3 h-3 mr-1" />
            )}
            Save Writing Plan
          </Button>
        </div>
      </div>
    </div>
  );
}
