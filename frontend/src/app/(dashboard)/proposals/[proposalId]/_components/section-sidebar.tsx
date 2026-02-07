"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { OutlineView } from "@/components/proposals/outline-view";
import type { Proposal, ProposalSection } from "@/types";

interface SectionSidebarProps {
  proposal: Proposal;
  sections: ProposalSection[];
  selectedSectionId: number | null;
  onSelectSection: (id: number) => void;
  proposalId: number;
  onOutlineApproved: () => void;
}

export function SectionSidebar({
  proposal,
  sections,
  selectedSectionId,
  onSelectSection,
  proposalId,
  onOutlineApproved,
}: SectionSidebarProps) {
  return (
    <>
      <Card className="border border-border h-full">
        <CardContent className="p-4 h-full flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm font-semibold text-foreground">Sections</p>
              <p className="text-xs text-muted-foreground">
                {proposal.completed_sections}/{proposal.total_sections} complete
              </p>
            </div>
          </div>
          <ScrollArea className="flex-1 -mx-2 px-2">
            <div className="space-y-2">
              {sections.length === 0 ? (
                <div className="text-sm text-muted-foreground">No sections yet.</div>
              ) : (
                sections.map((section) => (
                  <button
                    key={section.id}
                    type="button"
                    onClick={() => onSelectSection(section.id)}
                    className={`w-full text-left rounded-lg border px-3 py-2 transition-colors ${
                      selectedSectionId === section.id
                        ? "border-primary/40 bg-primary/10"
                        : "border-border hover:border-primary/30"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-muted-foreground font-mono">
                        {section.section_number}
                      </span>
                      <Badge variant="outline" className="text-[10px]">
                        {section.status}
                      </Badge>
                    </div>
                    <p className="text-sm text-foreground mt-1 line-clamp-2">
                      {section.title}
                    </p>
                  </button>
                ))
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
      <div className="mt-4">
        <OutlineView proposalId={proposalId} onApproved={onOutlineApproved} />
      </div>
    </>
  );
}
