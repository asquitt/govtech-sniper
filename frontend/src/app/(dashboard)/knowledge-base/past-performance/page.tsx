"use client";

import React, { useState } from "react";
import { Award, Target, Loader2 } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PastPerformanceLibrary } from "@/components/knowledge-base/past-performance-library";
import { PerformanceMetadataForm } from "@/components/knowledge-base/performance-metadata-form";
import { RelevanceResults } from "@/components/knowledge-base/relevance-results";
import { NarrativeGenerator } from "@/components/knowledge-base/narrative-generator";
import { pastPerformanceApi } from "@/lib/api";
import type { PastPerformanceDocument, MatchResult } from "@/types/past-performance";

export default function PastPerformancePage() {
  const [selectedDoc, setSelectedDoc] = useState<PastPerformanceDocument | null>(null);
  const [rfpIdInput, setRfpIdInput] = useState("");
  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [isMatching, setIsMatching] = useState(false);
  const [generatingId, setGeneratingId] = useState<number | undefined>();
  const [narrative, setNarrative] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleMatch = async () => {
    const rfpId = parseInt(rfpIdInput, 10);
    if (isNaN(rfpId)) return;

    setIsMatching(true);
    setNarrative(null);
    try {
      const res = await pastPerformanceApi.match(rfpId);
      setMatches(res.data.matches);
    } catch (err) {
      console.error("Match failed:", err);
      setMatches([]);
    } finally {
      setIsMatching(false);
    }
  };

  const handleGenerateNarrative = async (documentId: number) => {
    const rfpId = parseInt(rfpIdInput, 10);
    if (isNaN(rfpId)) return;

    setGeneratingId(documentId);
    try {
      const res = await pastPerformanceApi.generateNarrative(documentId, rfpId);
      setNarrative(res.data.narrative);
    } catch (err) {
      console.error("Narrative generation failed:", err);
    } finally {
      setGeneratingId(undefined);
    }
  };

  const handleSaved = () => {
    setSelectedDoc(null);
    setRefreshKey((k) => k + 1);
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Past Performance Library"
        description="Manage past performance records and match them to RFPs"
        actions={
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-amber-400" />
          </div>
        }
      />

      <div className="flex-1 p-6 overflow-auto space-y-6">
        {/* Metadata Form (shown when editing a doc) */}
        {selectedDoc && (
          <Card>
            <CardContent className="p-4">
              <PerformanceMetadataForm
                document={selectedDoc}
                onSaved={handleSaved}
                onCancel={() => setSelectedDoc(null)}
              />
            </CardContent>
          </Card>
        )}

        {/* Library Table */}
        <Card>
          <CardContent className="p-4">
            <h2 className="text-lg font-semibold mb-4">Past Performance Documents</h2>
            <PastPerformanceLibrary
              key={refreshKey}
              onSelectDocument={setSelectedDoc}
              selectedId={selectedDoc?.id}
            />
          </CardContent>
        </Card>

        {/* Match Section */}
        <Card>
          <CardContent className="p-4">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-primary" />
              Relevance Matching
            </h2>
            <div className="flex items-center gap-3 mb-4">
              <input
                type="number"
                placeholder="Enter RFP ID..."
                className="h-10 px-3 rounded-lg bg-secondary border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary w-48"
                value={rfpIdInput}
                onChange={(e) => setRfpIdInput(e.target.value)}
              />
              <Button onClick={handleMatch} disabled={!rfpIdInput || isMatching}>
                {isMatching ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-1" />
                ) : (
                  <Target className="w-4 h-4 mr-1" />
                )}
                Match
              </Button>
            </div>

            <RelevanceResults
              matches={matches}
              isLoading={isMatching}
              onGenerateNarrative={handleGenerateNarrative}
              generatingId={generatingId}
            />
          </CardContent>
        </Card>

        {/* Narrative Preview */}
        {narrative && (
          <NarrativeGenerator
            narrative={narrative}
            onClose={() => setNarrative(null)}
          />
        )}
      </div>
    </div>
  );
}
