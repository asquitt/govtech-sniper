"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Check, X, Eye, EyeOff, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Editor } from "@tiptap/react";
import { countAiSuggestions } from "./track-changes-extension";

interface SuggestionToolbarProps {
  editor: Editor | null;
}

export function SuggestionToolbar({ editor }: SuggestionToolbarProps) {
  const [showChanges, setShowChanges] = useState(true);
  const [suggestionCount, setSuggestionCount] = useState(0);

  // Recount suggestions whenever the document changes
  useEffect(() => {
    if (!editor) return;

    const updateCount = () => setSuggestionCount(countAiSuggestions(editor));
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

  if (!editor || suggestionCount === 0) return null;

  return (
    <div className="flex items-center gap-2 border-b border-border px-3 py-1.5 bg-yellow-50/50 dark:bg-yellow-900/10">
      <Sparkles className="w-3.5 h-3.5 text-yellow-600 dark:text-yellow-400" />
      <span className="text-xs font-medium text-yellow-700 dark:text-yellow-300">
        AI Suggestions
      </span>
      <Badge variant="warning" className="text-[10px] px-1.5 py-0">
        {suggestionCount}
      </Badge>

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
