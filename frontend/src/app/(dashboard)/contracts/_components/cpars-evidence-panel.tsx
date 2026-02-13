"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { contractApi } from "@/lib/api";
import type {
  CPARSReview,
  CPARSEvidence,
  KnowledgeBaseDocument,
} from "@/types";

interface CPARSEvidencePanelProps {
  selectedContractId: number | null;
  cpars: CPARSReview[];
  selectedCparsId: number | null;
  cparsEvidence: CPARSEvidence[];
  documents: KnowledgeBaseDocument[];
  onCparsChange: (cpars: CPARSReview[]) => void;
  onSelectedCparsIdChange: (id: number | null) => void;
  onCparsEvidenceChange: (evidence: CPARSEvidence[]) => void;
  onError: (msg: string) => void;
}

export function CPARSEvidencePanel({
  selectedContractId,
  cpars,
  selectedCparsId,
  cparsEvidence,
  documents,
  onCparsChange,
  onSelectedCparsIdChange,
  onCparsEvidenceChange,
  onError,
}: CPARSEvidencePanelProps) {
  const [cparsRating, setCparsRating] = useState("");
  const [cparsNotes, setCparsNotes] = useState("");
  const [evidenceDocumentId, setEvidenceDocumentId] = useState<number | null>(null);
  const [evidenceCitation, setEvidenceCitation] = useState("");
  const [evidenceNotes, setEvidenceNotes] = useState("");

  const handleCreateCPARS = async () => {
    if (!selectedContractId) return;
    try {
      const created = await contractApi.createCPARS(selectedContractId, {
        overall_rating: cparsRating.trim() || undefined,
        notes: cparsNotes.trim() || undefined,
      });
      setCparsRating("");
      setCparsNotes("");
      const list = await contractApi.listCPARS(selectedContractId);
      onCparsChange(list);
      onSelectedCparsIdChange(created.id);
    } catch (err) {
      console.error("Failed to create CPARS review", err);
      onError("Failed to create CPARS review.");
    }
  };

  const handleAddEvidence = async () => {
    if (!selectedContractId || !selectedCparsId || !evidenceDocumentId) return;
    try {
      await contractApi.addCPARSEvidence(selectedContractId, selectedCparsId, {
        document_id: evidenceDocumentId,
        citation: evidenceCitation.trim() || undefined,
        notes: evidenceNotes.trim() || undefined,
      });
      setEvidenceDocumentId(null);
      setEvidenceCitation("");
      setEvidenceNotes("");
      const list = await contractApi.listCPARSEvidence(
        selectedContractId,
        selectedCparsId
      );
      onCparsEvidenceChange(list);
    } catch (err) {
      console.error("Failed to add CPARS evidence", err);
      onError("Failed to add CPARS evidence.");
    }
  };

  const handleDeleteEvidence = async (evidenceId: number) => {
    if (!selectedContractId || !selectedCparsId) return;
    try {
      await contractApi.deleteCPARSEvidence(
        selectedContractId,
        selectedCparsId,
        evidenceId
      );
      const list = await contractApi.listCPARSEvidence(
        selectedContractId,
        selectedCparsId
      );
      onCparsEvidenceChange(list);
    } catch (err) {
      console.error("Failed to delete CPARS evidence", err);
      onError("Failed to delete CPARS evidence.");
    }
  };

  return (
    <>
      <div className="mt-6 space-y-3">
        <p className="text-sm font-medium">CPARS Reviews</p>
        <div className="flex gap-2">
          <input
            className="w-40 rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Rating"
            value={cparsRating}
            onChange={(e) => setCparsRating(e.target.value)}
          />
          <input
            className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Notes"
            value={cparsNotes}
            onChange={(e) => setCparsNotes(e.target.value)}
          />
          <Button onClick={handleCreateCPARS}>Add Review</Button>
        </div>
        <div className="space-y-2">
          {cpars.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No CPARS reviews yet.
            </p>
          ) : (
            cpars.map((review) => {
              const isSelected = review.id === selectedCparsId;
              return (
                <div
                  key={review.id}
                  className={cn(
                    "flex items-center justify-between rounded-md border px-3 py-2 text-sm cursor-pointer",
                    isSelected
                      ? "border-primary/50 bg-primary/10"
                      : "border-border hover:border-primary/30"
                  )}
                  onClick={() => onSelectedCparsIdChange(review.id)}
                >
                  <span>{review.overall_rating || "Unrated"}</span>
                  <Badge variant="outline">{review.created_at.slice(0, 10)}</Badge>
                </div>
              );
            })
          )}
        </div>
      </div>

      <div className="mt-4 space-y-3">
        <p className="text-sm font-medium">CPARS Evidence</p>
        {!selectedCparsId ? (
          <p className="text-sm text-muted-foreground">
            Select a CPARS review to link evidence.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-3 gap-2">
              <select
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                value={evidenceDocumentId ?? ""}
                onChange={(e) =>
                  setEvidenceDocumentId(
                    e.target.value ? Number(e.target.value) : null
                  )
                }
              >
                <option value="">Select document</option>
                {documents.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.title}
                  </option>
                ))}
              </select>
              <input
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Citation"
                value={evidenceCitation}
                onChange={(e) => setEvidenceCitation(e.target.value)}
              />
              <input
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Notes"
                value={evidenceNotes}
                onChange={(e) => setEvidenceNotes(e.target.value)}
              />
            </div>
            <Button onClick={handleAddEvidence}>Add Evidence</Button>
            <div className="space-y-2">
              {cparsEvidence.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No evidence linked yet.
                </p>
              ) : (
                cparsEvidence.map((evidence) => (
                  <div
                    key={evidence.id}
                    className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                  >
                    <div>
                      <p className="font-medium">
                        {evidence.document_title || `Document ${evidence.document_id}`}
                      </p>
                      {evidence.citation && (
                        <p className="text-xs text-muted-foreground">
                          {evidence.citation}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteEvidence(evidence.id)}
                    >
                      Remove
                    </Button>
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </div>
    </>
  );
}
