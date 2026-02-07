"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Check, FileText, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { draftApi } from "@/lib/api";
import type { KnowledgeBaseDocument, ProposalFocusDocument } from "@/types";

interface FocusDocumentSelectorProps {
  proposalId: number;
  documents: KnowledgeBaseDocument[];
  onUpdate?: () => void;
}

export function FocusDocumentSelector({
  proposalId,
  documents,
  onUpdate,
}: FocusDocumentSelectorProps) {
  const [focusDocs, setFocusDocs] = useState<ProposalFocusDocument[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isOpen, setIsOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const loadFocusDocs = useCallback(async () => {
    try {
      setIsLoading(true);
      const docs = await draftApi.listFocusDocuments(proposalId);
      setFocusDocs(docs);
      setSelectedIds(new Set(docs.map((d) => d.document_id)));
    } catch (err) {
      console.error("Failed to load focus documents", err);
    } finally {
      setIsLoading(false);
    }
  }, [proposalId]);

  useEffect(() => {
    loadFocusDocs();
  }, [loadFocusDocs]);

  const handleToggle = (docId: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) {
        next.delete(docId);
      } else {
        next.add(docId);
      }
      return next;
    });
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      const docs = await draftApi.setFocusDocuments(
        proposalId,
        Array.from(selectedIds)
      );
      setFocusDocs(docs);
      setIsOpen(false);
      onUpdate?.();
    } catch (err) {
      console.error("Failed to save focus documents", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleClear = async () => {
    try {
      setIsSaving(true);
      await draftApi.setFocusDocuments(proposalId, []);
      setFocusDocs([]);
      setSelectedIds(new Set());
      setIsOpen(false);
      onUpdate?.();
    } catch (err) {
      console.error("Failed to clear focus documents", err);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) {
    return (
      <Button variant="outline" size="sm" onClick={() => setIsOpen(true)}>
        <FileText className="w-4 h-4 mr-1" />
        Focus Docs
        {focusDocs.length > 0 && (
          <Badge variant="secondary" className="ml-1.5 text-[10px] px-1.5 py-0">
            {focusDocs.length}
          </Badge>
        )}
      </Button>
    );
  }

  return (
    <div className="border border-border rounded-lg bg-card p-3 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-foreground">Focus Documents</p>
          <p className="text-xs text-muted-foreground">
            Select which docs to use for generation. Empty = use all.
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setIsOpen(false)}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="max-h-48 overflow-y-auto space-y-1">
          {documents.map((doc) => {
            const isSelected = selectedIds.has(doc.id);
            return (
              <button
                key={doc.id}
                type="button"
                onClick={() => handleToggle(doc.id)}
                className={`w-full text-left flex items-center gap-2 px-2 py-1.5 rounded text-sm transition-colors ${
                  isSelected
                    ? "bg-primary/10 border border-primary/30"
                    : "hover:bg-secondary/50 border border-transparent"
                }`}
              >
                <div
                  className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
                    isSelected
                      ? "bg-primary border-primary text-primary-foreground"
                      : "border-border"
                  }`}
                >
                  {isSelected && <Check className="w-3 h-3" />}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-foreground truncate">{doc.title}</p>
                  <p className="text-[10px] text-muted-foreground truncate">
                    {doc.original_filename}
                  </p>
                </div>
                <Badge variant="outline" className="text-[10px] px-1.5 py-0 flex-shrink-0">
                  {doc.document_type}
                </Badge>
              </button>
            );
          })}
        </div>
      )}

      <div className="flex items-center gap-2">
        <Button
          size="sm"
          onClick={handleSave}
          disabled={isSaving}
          className="flex-1"
        >
          {isSaving ? (
            <Loader2 className="w-3 h-3 animate-spin mr-1" />
          ) : null}
          Save ({selectedIds.size} selected)
        </Button>
        {focusDocs.length > 0 && (
          <Button
            size="sm"
            variant="outline"
            onClick={handleClear}
            disabled={isSaving}
          >
            Clear
          </Button>
        )}
      </div>
    </div>
  );
}
