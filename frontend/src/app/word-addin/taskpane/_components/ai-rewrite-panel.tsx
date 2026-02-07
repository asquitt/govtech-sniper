"use client";

import React, { useState } from "react";
import { Check, Loader2, RotateCcw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { wordAddinSyncApi } from "@/lib/api/word-addin-client";
import {
  getSelectedText,
  replaceSelection,
  OfficeNotAvailableError,
} from "@/lib/office/word-document";

type RewriteMode = "shorten" | "expand" | "improve";

const MODES: { id: RewriteMode; label: string; desc: string }[] = [
  { id: "shorten", label: "Shorten", desc: "More concise, half the length" },
  { id: "expand", label: "Expand", desc: "Add detail and evidence" },
  { id: "improve", label: "Improve", desc: "Better clarity and persuasion" },
];

interface AiRewritePanelProps {
  isInOffice: boolean;
}

export function AiRewritePanel({ isInOffice }: AiRewritePanelProps) {
  const [mode, setMode] = useState<RewriteMode>("improve");
  const [isLoading, setIsLoading] = useState(false);
  const [original, setOriginal] = useState<string | null>(null);
  const [rewritten, setRewritten] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<{
    originalLen: number;
    rewrittenLen: number;
  } | null>(null);

  const handleRewrite = async () => {
    setIsLoading(true);
    setError(null);
    setOriginal(null);
    setRewritten(null);
    setStats(null);

    try {
      const selectedText = await getSelectedText();
      if (!selectedText.trim()) {
        setError("Select text in the Word document first.");
        return;
      }

      setOriginal(selectedText);
      const result = await wordAddinSyncApi.rewriteContent(selectedText, mode);
      setRewritten(result.rewritten);
      setStats({
        originalLen: result.original_length,
        rewrittenLen: result.rewritten_length,
      });
    } catch (err) {
      if (err instanceof OfficeNotAvailableError) {
        setError("Open in Word to use AI rewrite.");
      } else {
        setError(err instanceof Error ? err.message : "Rewrite failed");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleAccept = async () => {
    if (!rewritten) return;
    try {
      await replaceSelection(rewritten);
      setOriginal(null);
      setRewritten(null);
      setStats(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Replace failed");
    }
  };

  const handleCancel = () => {
    setOriginal(null);
    setRewritten(null);
    setStats(null);
    setError(null);
  };

  return (
    <div className="space-y-3">
      {/* Mode selector */}
      <div className="space-y-1">
        <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">
          Mode
        </p>
        <div className="flex gap-1">
          {MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={`flex-1 rounded-md border px-2 py-1.5 text-[11px] transition-colors ${
                mode === m.id
                  ? "border-primary bg-primary/10 text-primary font-medium"
                  : "border-border text-muted-foreground hover:bg-accent/50"
              }`}
              title={m.desc}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* Rewrite button */}
      <Button
        size="sm"
        className="w-full text-xs"
        onClick={handleRewrite}
        disabled={isLoading || !isInOffice}
      >
        {isLoading ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : (
          <RotateCcw className="w-3 h-3" />
        )}
        Rewrite Selection
      </Button>

      {/* Error */}
      {error && (
        <p className="text-[11px] text-red-500 bg-red-500/10 border border-red-500/30 rounded-md px-2 py-1.5">
          {error}
        </p>
      )}

      {/* Preview */}
      {rewritten && (
        <div className="space-y-2">
          {/* Stats */}
          {stats && (
            <p className="text-[10px] text-muted-foreground">
              {stats.originalLen} → {stats.rewrittenLen} chars (
              {stats.rewrittenLen > stats.originalLen ? "+" : ""}
              {Math.round(
                ((stats.rewrittenLen - stats.originalLen) /
                  stats.originalLen) *
                  100
              )}
              %)
            </p>
          )}

          {/* Original */}
          {original && (
            <div className="rounded-md border border-border bg-red-500/5 p-2">
              <p className="text-[10px] text-muted-foreground font-medium mb-1">
                Original
              </p>
              <p className="text-[11px] text-muted-foreground line-through line-clamp-4">
                {original}
              </p>
            </div>
          )}

          {/* Rewritten */}
          <div className="rounded-md border border-primary/30 bg-primary/5 p-2">
            <p className="text-[10px] text-primary font-medium mb-1">
              Rewritten
            </p>
            <p className="text-[11px] line-clamp-6">{rewritten}</p>
          </div>

          {/* Accept / Cancel */}
          <div className="flex gap-2">
            <Button
              size="sm"
              className="flex-1 text-xs"
              onClick={handleAccept}
            >
              <Check className="w-3 h-3" />
              Accept
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="flex-1 text-xs"
              onClick={handleCancel}
            >
              <X className="w-3 h-3" />
              Cancel
            </Button>
          </div>
        </div>
      )}

      {!isInOffice && !error && (
        <p className="text-[10px] text-muted-foreground text-center">
          Open this page inside Word to select and rewrite text.
        </p>
      )}
    </div>
  );
}
