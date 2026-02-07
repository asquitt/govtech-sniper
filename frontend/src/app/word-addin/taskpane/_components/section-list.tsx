"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  Circle,
  Clock,
  Loader2,
  Pencil,
  Sparkles,
} from "lucide-react";
import { draftApi } from "@/lib/api/draft";
import type { ProposalSection, SectionStatus } from "@/types";

interface SectionListProps {
  proposalId: number | null;
  selectedSectionId: number | null;
  onSelectSection: (section: ProposalSection) => void;
}

const STATUS_CONFIG: Record<
  SectionStatus,
  { icon: React.ElementType; color: string; label: string }
> = {
  pending: { icon: Circle, color: "text-muted-foreground", label: "Pending" },
  generating: {
    icon: Sparkles,
    color: "text-yellow-500",
    label: "Generating",
  },
  generated: {
    icon: CheckCircle2,
    color: "text-blue-500",
    label: "Generated",
  },
  editing: { icon: Pencil, color: "text-orange-500", label: "Editing" },
  approved: {
    icon: CheckCircle2,
    color: "text-green-500",
    label: "Approved",
  },
};

export function SectionList({
  proposalId,
  selectedSectionId,
  onSelectSection,
}: SectionListProps) {
  const [sections, setSections] = useState<ProposalSection[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const load = useCallback(async () => {
    if (!proposalId) return;
    try {
      setIsLoading(true);
      const data = await draftApi.listSections(proposalId);
      setSections(data);
    } catch {
      console.error("Failed to load sections");
    } finally {
      setIsLoading(false);
    }
  }, [proposalId]);

  useEffect(() => {
    load();
  }, [load]);

  if (!proposalId) {
    return (
      <p className="text-xs text-muted-foreground py-2">
        Select a proposal above.
      </p>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-4">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (sections.length === 0) {
    return (
      <p className="text-xs text-muted-foreground py-2">
        No sections yet. Generate from compliance matrix in the web app.
      </p>
    );
  }

  return (
    <div className="space-y-1 max-h-[300px] overflow-y-auto">
      {sections.map((section) => {
        const status = STATUS_CONFIG[section.status] || STATUS_CONFIG.pending;
        const StatusIcon = status.icon;
        const isSelected = section.id === selectedSectionId;

        return (
          <button
            key={section.id}
            onClick={() => onSelectSection(section)}
            className={`w-full text-left rounded-md border px-2 py-1.5 transition-colors ${
              isSelected
                ? "border-primary bg-primary/10"
                : "border-border hover:bg-accent/50"
            }`}
          >
            <div className="flex items-center gap-1.5">
              <StatusIcon className={`w-3 h-3 shrink-0 ${status.color}`} />
              <span className="text-[11px] font-medium text-muted-foreground">
                {section.section_number}
              </span>
              <span className="text-xs truncate flex-1">{section.title}</span>
            </div>
            {section.word_count != null && section.word_count > 0 && (
              <div className="text-[10px] text-muted-foreground mt-0.5 ml-4">
                {section.word_count} words · {status.label}
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}
