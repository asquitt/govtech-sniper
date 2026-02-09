"use client";

import React, { useCallback, useEffect, useState } from "react";
import { ChevronDown, FileText, Loader2 } from "lucide-react";
import { draftApi } from "@/lib/api/draft";
import type { Proposal } from "@/types";

interface ProposalSelectorProps {
  selectedId: number | null;
  onSelect: (proposal: Proposal) => void;
}

export function ProposalSelector({
  selectedId,
  onSelect,
}: ProposalSelectorProps) {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);

  const load = useCallback(async (isMounted: () => boolean) => {
    try {
      if (!isMounted()) return;
      setIsLoading(true);
      const data = await draftApi.listProposals();
      if (!isMounted()) return;
      setProposals(data);
    } catch {
      console.error("Failed to load proposals");
    } finally {
      if (isMounted()) {
        setIsLoading(false);
      }
    }
  }, [selectedId, onSelect]);

  useEffect(() => {
    let mounted = true;
    const isMounted = () => mounted;
    void load(isMounted);
    return () => {
      mounted = false;
    };
  }, [load]);

  useEffect(() => {
    if (!selectedId && proposals.length > 0) {
      onSelect(proposals[0]);
    }
  }, [selectedId, proposals, onSelect]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-2">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (proposals.length === 0) {
    return (
      <p className="text-xs text-muted-foreground py-2">
        No proposals found. Create one in the web app first.
      </p>
    );
  }

  const selected = proposals.find((p) => p.id === selectedId);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between gap-2 rounded-md border border-border bg-background px-2 py-1.5 text-sm hover:bg-accent/50 transition-colors"
      >
        <div className="flex items-center gap-1.5 min-w-0">
          <FileText className="w-3.5 h-3.5 shrink-0 text-primary" />
          <span className="truncate">
            {selected?.title || "Select proposal..."}
          </span>
        </div>
        <ChevronDown className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
      </button>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 rounded-md border border-border bg-card shadow-lg max-h-48 overflow-y-auto">
          {proposals.map((p) => (
            <button
              key={p.id}
              onClick={() => {
                onSelect(p);
                setIsOpen(false);
              }}
              className={`w-full text-left px-2 py-1.5 text-sm hover:bg-accent/50 transition-colors ${
                p.id === selectedId ? "bg-accent/30" : ""
              }`}
            >
              <div className="truncate font-medium">{p.title}</div>
              <div className="text-[10px] text-muted-foreground">
                {p.status} · {p.completed_sections}/{p.total_sections} sections
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
