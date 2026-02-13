"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Check, X, Eye, EyeOff, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Editor } from "@tiptap/react";
import { countAiSuggestions } from "./track-changes-extension";

interface SuggestionMeta {
  author: string;
  timestamp: string | null;
  suggestionId: string | null;
  from: number;
  to: number;
}

interface SuggestionToolbarProps {
  editor: Editor | null;
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return "";
  try {
    return new Date(ts).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

/** Collect metadata for each distinct suggestion range in the document. */
function collectSuggestions(editor: Editor): SuggestionMeta[] {
  const results: SuggestionMeta[] = [];
  const markType = editor.state.schema.marks.aiSuggestion;
  if (!markType) return results;

  let current: SuggestionMeta | null = null;

  editor.state.doc.descendants((node, pos) => {
    const mark = markType.isInSet(node.marks);
    if (mark) {
      const end = pos + node.nodeSize;
      if (current && current.to === pos && current.suggestionId === (mark.attrs.suggestionId ?? null)) {
        current.to = end;
      } else {
        current = {
          author: mark.attrs.author ?? "AI",
          timestamp: mark.attrs.timestamp ?? null,
          suggestionId: mark.attrs.suggestionId ?? null,
          from: pos,
          to: end,
        };
        results.push(current);
      }
    } else {
      current = null;
    }
  });

  return results;
}

export function SuggestionToolbar({ editor }: SuggestionToolbarProps) {
  const [showChanges, setShowChanges] = useState(true);
  const [suggestionCount, setSuggestionCount] = useState(0);
  const [suggestions, setSuggestions] = useState<SuggestionMeta[]>([]);
  const [activeSuggestion, setActiveSuggestion] = useState<number>(0);

  // Recount suggestions whenever the document changes
  useEffect(() => {
    if (!editor) return;

    const updateCount = () => {
      setSuggestionCount(countAiSuggestions(editor));
      setSuggestions(collectSuggestions(editor));
    };
    updateCount();

    editor.on("update", updateCount);
    return () => {
      editor.off("update", updateCount);
    };
  }, [editor]);

  const toggleVisibility = useCallback(() => {
    setShowChanges((prev) => !prev);
  }, []);

  const acceptAll = useCallback(() => {
    if (!editor) return;
    editor.chain().focus().acceptAllSuggestions().run();
  }, [editor]);

  const rejectAll = useCallback(() => {
    if (!editor) return;
    editor.chain().focus().rejectAllSuggestions().run();
  }, [editor]);

  const acceptCurrent = useCallback(() => {
    if (!editor || suggestions.length === 0) return;
    const s = suggestions[activeSuggestion];
    if (!s) return;
    editor.chain().focus().setTextSelection({ from: s.from, to: s.to }).acceptSuggestion().run();
  }, [editor, suggestions, activeSuggestion]);

  const rejectCurrent = useCallback(() => {
    if (!editor || suggestions.length === 0) return;
    const s = suggestions[activeSuggestion];
    if (!s) return;
    editor.chain().focus().setTextSelection({ from: s.from, to: s.to }).rejectSuggestion().run();
  }, [editor, suggestions, activeSuggestion]);

  // Clamp active index when suggestions change
  useEffect(() => {
    if (activeSuggestion >= suggestions.length) {
      setActiveSuggestion(Math.max(0, suggestions.length - 1));
    }
  }, [suggestions.length, activeSuggestion]);

  if (!editor || suggestionCount === 0) return null;

  const current = suggestions[activeSuggestion];
  const meta = current
    ? `${current.author}${current.timestamp ? " \u00B7 " + formatTimestamp(current.timestamp) : ""}`
    : "";

  return (
    <div className="flex items-center gap-2 border-b border-border px-3 py-1.5 bg-yellow-50/50 dark:bg-yellow-900/10">
      <Sparkles className="w-3.5 h-3.5 text-yellow-600 dark:text-yellow-400" />
      <span className="text-xs font-medium text-yellow-700 dark:text-yellow-300">
        AI Suggestions
      </span>
      <Badge variant="warning" className="text-[10px] px-1.5 py-0">
        {suggestionCount}
      </Badge>

      {/* Per-suggestion navigation + accept/reject */}
      {suggestions.length > 0 && (
        <>
          <div className="w-px h-4 bg-border" />
          <span className="text-[10px] text-muted-foreground truncate max-w-[180px]" title={meta}>
            {activeSuggestion + 1}/{suggestions.length} {meta ? `\u2014 ${meta}` : ""}
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-5 w-5 p-0 text-green-600 hover:text-green-700 hover:bg-green-50"
            onClick={acceptCurrent}
            title="Accept this suggestion"
            type="button"
          >
            <Check className="w-3 h-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-5 w-5 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
            onClick={rejectCurrent}
            title="Reject this suggestion"
            type="button"
          >
            <X className="w-3 h-3" />
          </Button>
          {suggestions.length > 1 && (
            <>
              <Button
                variant="ghost"
                size="sm"
                className="h-5 px-1 text-[10px]"
                onClick={() => setActiveSuggestion((i) => (i > 0 ? i - 1 : suggestions.length - 1))}
                type="button"
              >
                Prev
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-5 px-1 text-[10px]"
                onClick={() => setActiveSuggestion((i) => (i < suggestions.length - 1 ? i + 1 : 0))}
                type="button"
              >
                Next
              </Button>
            </>
          )}
        </>
      )}

      <div className="flex-1" />

      <Button
        variant="ghost"
        size="sm"
        className="h-6 px-2 text-xs gap-1"
        onClick={toggleVisibility}
        title={showChanges ? "Hide suggestions" : "Show suggestions"}
        type="button"
      >
        {showChanges ? (
          <EyeOff className="w-3 h-3" />
        ) : (
          <Eye className="w-3 h-3" />
        )}
        {showChanges ? "Hide" : "Show"}
      </Button>

      <div className="w-px h-4 bg-border" />

      <Button
        variant="ghost"
        size="sm"
        className="h-6 px-2 text-xs gap-1 text-green-600 hover:text-green-700 hover:bg-green-50"
        onClick={acceptAll}
        title="Accept all AI suggestions"
        type="button"
      >
        <Check className="w-3 h-3" />
        Accept All
      </Button>

      <Button
        variant="ghost"
        size="sm"
        className="h-6 px-2 text-xs gap-1 text-red-600 hover:text-red-700 hover:bg-red-50"
        onClick={rejectAll}
        title="Reject all AI suggestions"
        type="button"
      >
        <X className="w-3 h-3" />
        Reject All
      </Button>

      {/* Inject a style tag to toggle highlight visibility */}
      {!showChanges && (
        <style>{`.ai-suggestion { background: none !important; border-bottom: none !important; text-decoration: none !important; }`}</style>
      )}
    </div>
  );
}
