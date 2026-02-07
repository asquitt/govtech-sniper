"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type {
  DataSourceSearchResponse,
  DataSourceIngestResponse,
} from "@/types/data-sources";

interface SearchResultsProps {
  searchResults: DataSourceSearchResponse | null;
  ingestResult: DataSourceIngestResponse | null;
}

export function IngestSummary({ ingestResult }: { ingestResult: DataSourceIngestResponse }) {
  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-2">
        <p className="text-sm font-medium">Ingest Complete</p>
        <div className="grid grid-cols-3 gap-3 text-sm">
          <div className="rounded-md border border-border px-3 py-2">
            <p className="text-xs text-muted-foreground">Searched</p>
            <p className="text-lg font-semibold">{ingestResult.searched}</p>
          </div>
          <div className="rounded-md border border-border px-3 py-2">
            <p className="text-xs text-muted-foreground">Created</p>
            <p className="text-lg font-semibold">{ingestResult.created}</p>
          </div>
          <div className="rounded-md border border-border px-3 py-2">
            <p className="text-xs text-muted-foreground">Skipped (duplicates)</p>
            <p className="text-lg font-semibold">{ingestResult.skipped}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function SearchResults({ searchResults }: { searchResults: DataSourceSearchResponse }) {
  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-3">
        <p className="text-sm font-medium">
          Results ({searchResults.count})
        </p>
        {searchResults.results.length === 0 ? (
          <p className="text-sm text-muted-foreground">No opportunities found.</p>
        ) : (
          <div className="space-y-2">
            {searchResults.results.map((opp) => (
              <div
                key={opp.external_id}
                className="rounded-md border border-border px-3 py-3 space-y-1 text-sm"
              >
                <div className="flex items-center justify-between">
                  <p className="font-medium text-foreground line-clamp-1">
                    {opp.title}
                  </p>
                  <Badge variant="outline">{opp.source_type}</Badge>
                </div>
                {opp.agency && (
                  <p className="text-xs text-muted-foreground">{opp.agency}</p>
                )}
                <div className="flex gap-4 text-xs text-muted-foreground">
                  {opp.posted_date && <span>Posted: {opp.posted_date}</span>}
                  {opp.response_deadline && (
                    <span>Deadline: {opp.response_deadline}</span>
                  )}
                  {opp.estimated_value != null && (
                    <span>Value: ${opp.estimated_value.toLocaleString()}</span>
                  )}
                  {opp.naics_code && <span>NAICS: {opp.naics_code}</span>}
                </div>
                {opp.description && (
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {opp.description}
                  </p>
                )}
                {opp.source_url && (
                  <a
                    href={opp.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary underline"
                  >
                    View Source
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
