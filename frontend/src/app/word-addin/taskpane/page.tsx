"use client";

import React, { useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { useOffice } from "@/hooks/useOffice";
import { AddinAuthGate } from "./_components/addin-auth-gate";
import { ProposalSelector } from "./_components/proposal-selector";
import { SectionList } from "./_components/section-list";
import { SectionSyncPanel } from "./_components/section-sync-panel";
import { AiRewritePanel } from "./_components/ai-rewrite-panel";
import type { Proposal, ProposalSection } from "@/types";

type TabId = "sections" | "sync" | "rewrite" | "compliance" | "search" | "generate";

const TABS: { id: TabId; label: string }[] = [
  { id: "sections", label: "Sections" },
  { id: "sync", label: "Sync" },
  { id: "rewrite", label: "Rewrite" },
  { id: "compliance", label: "Check" },
  { id: "search", label: "Search" },
  { id: "generate", label: "Generate" },
];

export default function TaskPanePage() {
  const { isReady, isInOffice, isLoading: officeLoading } = useOffice();
  const [selectedProposal, setSelectedProposal] = useState<Proposal | null>(
    null
  );
  const [selectedSection, setSelectedSection] =
    useState<ProposalSection | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("sections");

  if (officeLoading || !isReady) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <AddinAuthGate>
      <div className="space-y-3">
        {/* Office.js status banner */}
        {!isInOffice && (
          <div className="flex items-center gap-1.5 rounded-md bg-yellow-500/10 border border-yellow-500/30 px-2 py-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-yellow-500 shrink-0" />
            <p className="text-[11px] text-yellow-600">
              Running outside Word. Open this page inside Microsoft Word to
              enable document sync.
            </p>
          </div>
        )}

        {/* Proposal selector */}
        <ProposalSelector
          selectedId={selectedProposal?.id ?? null}
          onSelect={setSelectedProposal}
        />

        {/* Tab navigation */}
        <div className="flex gap-0.5 border-b border-border overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-2 py-1 text-[11px] font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === "sections" && (
          <SectionList
            proposalId={selectedProposal?.id ?? null}
            selectedSectionId={selectedSection?.id ?? null}
            onSelectSection={setSelectedSection}
          />
        )}

        {activeTab === "sync" && (
          <SectionSyncPanel
            section={selectedSection}
            isInOffice={isInOffice}
          />
        )}

        {activeTab === "rewrite" && (
          <AiRewritePanel isInOffice={isInOffice} />
        )}

        {activeTab === "compliance" && (
          <p className="text-xs text-muted-foreground py-4 text-center">
            Compliance check panel — coming next.
          </p>
        )}

        {activeTab === "search" && (
          <p className="text-xs text-muted-foreground py-4 text-center">
            Knowledge base search — coming next.
          </p>
        )}

        {activeTab === "generate" && (
          <p className="text-xs text-muted-foreground py-4 text-center">
            Section generation — coming next.
          </p>
        )}

        {/* Selected section info (shown when not on sync tab) */}
        {selectedSection && activeTab !== "sync" && (
          <div className="rounded-md border border-border bg-card/50 p-2">
            <p className="text-[10px] text-muted-foreground">
              Selected Section
            </p>
            <p className="text-xs font-medium truncate">
              {selectedSection.section_number}: {selectedSection.title}
            </p>
          </div>
        )}
      </div>
    </AddinAuthGate>
  );
}
