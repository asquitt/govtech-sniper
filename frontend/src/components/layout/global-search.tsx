"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { searchApi } from "@/lib/api/search";
import type { SearchResult } from "@/types/search";

const ENTITY_LABELS: Record<string, string> = {
  rfp: "Opportunity",
  proposal_section: "Proposal",
  knowledge_doc: "Knowledge Base",
  contact: "Contact",
};

const ENTITY_COLORS: Record<string, string> = {
  rfp: "bg-blue-100 text-blue-800",
  proposal_section: "bg-green-100 text-green-800",
  knowledge_doc: "bg-purple-100 text-purple-800",
  contact: "bg-orange-100 text-orange-800",
};

function getEntityRoute(result: SearchResult): string {
  switch (result.entity_type) {
    case "rfp":
      return `/opportunities/${result.entity_id}`;
    case "proposal_section":
      return `/proposals/${result.entity_id}`;
    case "knowledge_doc":
      return `/knowledge-base/${result.entity_id}`;
    case "contact":
      return `/contacts/${result.entity_id}`;
    default:
      return "#";
  }
}

export function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const router = useRouter();

  // Cmd+K / Ctrl+K to open
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
      setResults([]);
      setSelectedIndex(0);
    }
  }, [open]);

  // Debounced search
  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const resp = await searchApi.search({ query: q, limit: 10 });
      setResults(resp.data.results);
      setSelectedIndex(0);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleInputChange = (val: string) => {
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(val), 300);
  };

  const navigate = (result: SearchResult) => {
    setOpen(false);
    router.push(getEntityRoute(result));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      setOpen(false);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter" && results[selectedIndex]) {
      navigate(results[selectedIndex]);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />

      {/* Dialog */}
      <div className="relative w-full max-w-lg rounded-xl border bg-white shadow-2xl">
        {/* Search input */}
        <div className="flex items-center border-b px-4">
          <svg
            className="mr-2 h-4 w-4 shrink-0 text-muted-foreground"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
            />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search opportunities, proposals, documents..."
            className="flex-1 border-0 bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground"
          />
          <kbd className="ml-2 rounded border bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[300px] overflow-y-auto p-2">
          {loading && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              Searching...
            </p>
          )}

          {!loading && query.length >= 2 && results.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No results found.
            </p>
          )}

          {!loading && query.length < 2 && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              Type at least 2 characters to search.
            </p>
          )}

          {results.map((result, i) => (
            <button
              key={`${result.entity_type}-${result.entity_id}-${result.chunk_index}`}
              onClick={() => navigate(result)}
              className={`flex w-full items-start gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                i === selectedIndex
                  ? "bg-accent text-accent-foreground"
                  : "hover:bg-accent/50"
              }`}
            >
              <span
                className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${
                  ENTITY_COLORS[result.entity_type] ?? "bg-gray-100 text-gray-800"
                }`}
              >
                {ENTITY_LABELS[result.entity_type] ?? result.entity_type}
              </span>
              <span className="line-clamp-2 flex-1 text-muted-foreground">
                {result.chunk_text.slice(0, 120)}
                {result.chunk_text.length > 120 ? "..." : ""}
              </span>
              <span className="mt-0.5 shrink-0 text-[10px] text-muted-foreground">
                {(result.score * 100).toFixed(0)}%
              </span>
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t px-4 py-2 text-[10px] text-muted-foreground">
          <span>
            <kbd className="rounded border bg-muted px-1 py-0.5 font-mono">
              &uarr;&darr;
            </kbd>{" "}
            Navigate
          </span>
          <span>
            <kbd className="rounded border bg-muted px-1 py-0.5 font-mono">
              Enter
            </kbd>{" "}
            Open
          </span>
        </div>
      </div>
    </div>
  );
}
