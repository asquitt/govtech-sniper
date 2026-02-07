"use client";

import React from "react";
import { Link2, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { SectionEvidence, KnowledgeBaseDocument } from "@/types";

interface EvidencePanelProps {
  evidence: SectionEvidence[];
  documents: KnowledgeBaseDocument[];
  selectedDocumentId: number | null;
  onDocumentChange: (id: number | null) => void;
  citationText: string;
  onCitationChange: (text: string) => void;
  notesText: string;
  onNotesChange: (text: string) => void;
  onAddEvidence: () => void;
  disabled: boolean;
}

export function EvidencePanel({
  evidence,
  documents,
  selectedDocumentId,
  onDocumentChange,
  citationText,
  onCitationChange,
  notesText,
  onNotesChange,
  onAddEvidence,
  disabled,
}: EvidencePanelProps) {
  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Link2 className="w-4 h-4 text-primary" />
          <p className="text-sm font-semibold">Evidence</p>
        </div>
        <div className="space-y-2 text-xs text-muted-foreground">
          {evidence.length === 0 ? (
            <p>No evidence linked yet.</p>
          ) : (
            evidence.map((link) => (
              <div key={link.id} className="border border-border rounded-md p-2">
                <p className="text-sm text-foreground">
                  {link.document_title || link.document_filename || "Document"}
                </p>
                {link.citation && <p className="text-xs">{link.citation}</p>}
              </div>
            ))
          )}
        </div>
        <div className="space-y-2">
          <select
            className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
            value={selectedDocumentId ?? ""}
            onChange={(e) => onDocumentChange(Number(e.target.value) || null)}
          >
            <option value="">Select document</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.title}
              </option>
            ))}
          </select>
          <input
            className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Citation or page reference"
            value={citationText}
            onChange={(e) => onCitationChange(e.target.value)}
          />
          <input
            className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Notes"
            value={notesText}
            onChange={(e) => onNotesChange(e.target.value)}
          />
          <Button
            variant="outline"
            className="w-full"
            onClick={onAddEvidence}
            disabled={disabled || !selectedDocumentId}
          >
            <Plus className="w-4 h-4" />
            Add Evidence
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
