"use client";

import React from "react";
import { Target, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { MatchResult } from "@/types/past-performance";

interface RelevanceResultsProps {
  matches: MatchResult[];
  isLoading: boolean;
  onGenerateNarrative: (documentId: number) => void;
  generatingId?: number;
}

function getScoreColor(score: number): string {
  if (score >= 70) return "text-green-400";
  if (score >= 40) return "text-amber-400";
  return "text-red-400";
}

function getScoreBg(score: number): string {
  if (score >= 70) return "bg-green-400/10 border-green-400/20";
  if (score >= 40) return "bg-amber-400/10 border-amber-400/20";
  return "bg-red-400/10 border-red-400/20";
}

export function RelevanceResults({ matches, isLoading, onGenerateNarrative, generatingId }: RelevanceResultsProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Matching past performances...</span>
      </div>
    );
  }

  if (matches.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
        <Target className="w-8 h-8 mb-2" />
        <p>No matching past performances found</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {matches.map((match) => (
        <div
          key={match.document_id}
          className={`p-4 rounded-lg border ${getScoreBg(match.score)}`}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span className={`text-2xl font-bold ${getScoreColor(match.score)}`}>
                  {Math.round(match.score)}
                </span>
                <div>
                  <h4 className="font-medium text-foreground">{match.title}</h4>
                  <p className="text-xs text-muted-foreground">Relevance Score</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {match.matching_criteria.map((criterion, idx) => (
                  <Badge key={idx} variant="secondary" className="text-xs">
                    {criterion}
                  </Badge>
                ))}
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onGenerateNarrative(match.document_id)}
              disabled={generatingId === match.document_id}
            >
              {generatingId === match.document_id ? (
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
              ) : (
                <FileText className="w-4 h-4 mr-1" />
              )}
              Narrative
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
