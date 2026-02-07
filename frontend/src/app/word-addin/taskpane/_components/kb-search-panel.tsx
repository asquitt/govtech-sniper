"use client";

import React, { useState, useRef, useCallback } from "react";
import { Loader2, Search, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { searchApi } from "@/lib/api/search";
import { insertAtCursor, OfficeNotAvailableError } from "@/lib/office/word-document";
import type { SearchResult } from "@/types/search";

interface KbSearchPanelProps {
  isInOffice: boolean;
}

export function KbSearchPanel({ isInOffice }: KbSearchPanelProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [insertingId, setInsertingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    setIsSearching(true);
    setError(null);
    try {
      const res = await searchApi.search({ query: q, limit: 10 });
      setResults(res.data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setIsSearching(false);
    }
  }, []);

  const handleInputChange = (value: string) => {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(value), 300);
  };

  const handleInsert = async (result: SearchResult) => {
    setInsertingId(result.entity_id);
    try {
      const text = `${result.chunk_text}\n[Source: ${result.entity_type} #${result.entity_id}]`;
      await insertAtCursor(text);
    } catch (err) {
      if (err instanceof OfficeNotAvailableError) {
        setError("Open in Word to insert text.");
      } else {
        setError(err instanceof Error ? err.message : "Insert failed");
      }
    } finally {
      setInsertingId(null);
    }
  };

  return (
    <div className="space-y-3">
      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search knowledge base..."
          value={query}
          onChange={(e) => handleInputChange(e.target.value)}
          className="w-full rounded-md border border-border bg-background pl-7 pr-2 py-1.5 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      {/* Loading */}
      {isSearching && (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-[11px] text-red-500 bg-red-500/10 border border-red-500/30 rounded-md px-2 py-1.5">
          {error}
        </p>
      )}

      {/* Results */}
      {!isSearching && results.length > 0 && (
        <div className="space-y-1.5">
          {results.map((r, i) => (
            <div
              key={`${r.entity_type}-${r.entity_id}-${r.chunk_index}`}
              className="rounded-md border border-border bg-card/50 p-2 space-y-1"
            >
              <div className="flex items-center justify-between gap-1">
                <span className="text-[10px] text-muted-foreground font-medium uppercase">
                  {r.entity_type}
                </span>
                <span className="text-[10px] text-muted-foreground">
                  {Math.round(r.score * 100)}%
                </span>
              </div>
              <p className="text-[11px] line-clamp-3">{r.chunk_text}</p>
              <Button
                size="sm"
                variant="outline"
                className="w-full text-[10px] h-6"
                onClick={() => handleInsert(r)}
                disabled={!isInOffice || insertingId === r.entity_id}
              >
                {insertingId === r.entity_id ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Plus className="w-3 h-3" />
                )}
                Insert at Cursor
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isSearching && query.trim() && results.length === 0 && !error && (
        <p className="text-[10px] text-muted-foreground text-center py-4">
          No results found.
        </p>
      )}

      {!isInOffice && !error && (
        <p className="text-[10px] text-muted-foreground text-center">
          Open in Word to insert search results into the document.
        </p>
      )}
    </div>
  );
}
