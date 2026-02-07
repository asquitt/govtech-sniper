"use client";

import React, { useState } from "react";
import { ArrowDown, ArrowUp, CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { wordAddinSyncApi } from "@/lib/api/word-addin-client";
import {
  insertSectionContent,
  getSelectedText,
  OfficeNotAvailableError,
} from "@/lib/office/word-document";
import type { ProposalSection } from "@/types";

interface SectionSyncPanelProps {
  section: ProposalSection | null;
  isInOffice: boolean;
}

export function SectionSyncPanel({
  section,
  isInOffice,
}: SectionSyncPanelProps) {
  const [isPulling, setIsPulling] = useState(false);
  const [isPushing, setIsPushing] = useState(false);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  if (!section) {
    return (
      <p className="text-xs text-muted-foreground py-4 text-center">
        Select a section from the Sections tab to sync.
      </p>
    );
  }

  const handlePull = async () => {
    setIsPulling(true);
    setMessage(null);
    try {
      const data = await wordAddinSyncApi.pullSection(section.id);
      await insertSectionContent(data.title, data.content);
      setMessage({
        type: "success",
        text: `Inserted "${data.title}" (${data.content.length} chars)`,
      });
    } catch (err) {
      if (err instanceof OfficeNotAvailableError) {
        setMessage({ type: "error", text: "Open in Word to use document sync." });
      } else {
        setMessage({
          type: "error",
          text: err instanceof Error ? err.message : "Pull failed",
        });
      }
    } finally {
      setIsPulling(false);
    }
  };

  const handlePush = async () => {
    setIsPushing(true);
    setMessage(null);
    try {
      const text = await getSelectedText();
      if (!text.trim()) {
        setMessage({
          type: "error",
          text: "Select text in Word first, then push.",
        });
        return;
      }
      await wordAddinSyncApi.pushSection(section.id, text);
      setMessage({
        type: "success",
        text: `Pushed ${text.length} chars to section.`,
      });
    } catch (err) {
      if (err instanceof OfficeNotAvailableError) {
        setMessage({ type: "error", text: "Open in Word to use document sync." });
      } else {
        setMessage({
          type: "error",
          text: err instanceof Error ? err.message : "Push failed",
        });
      }
    } finally {
      setIsPushing(false);
    }
  };

  return (
    <div className="space-y-3">
      {/* Section info */}
      <div className="rounded-md border border-border bg-card/50 p-2 space-y-1">
        <p className="text-xs font-medium">
          {section.section_number}: {section.title}
        </p>
        {section.requirement_text && (
          <p className="text-[10px] text-muted-foreground line-clamp-3">
            {section.requirement_text}
          </p>
        )}
      </div>

      {/* Sync buttons */}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="outline"
          className="flex-1 text-xs"
          onClick={handlePull}
          disabled={isPulling || !isInOffice}
        >
          {isPulling ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <ArrowDown className="w-3 h-3" />
          )}
          Pull into Word
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="flex-1 text-xs"
          onClick={handlePush}
          disabled={isPushing || !isInOffice}
        >
          {isPushing ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <ArrowUp className="w-3 h-3" />
          )}
          Push from Word
        </Button>
      </div>

      {/* Status message */}
      {message && (
        <div
          className={`flex items-center gap-1.5 rounded-md px-2 py-1.5 text-[11px] ${
            message.type === "success"
              ? "bg-green-500/10 text-green-600 border border-green-500/30"
              : "bg-red-500/10 text-red-600 border border-red-500/30"
          }`}
        >
          {message.type === "success" && (
            <CheckCircle2 className="w-3 h-3 shrink-0" />
          )}
          {message.text}
        </div>
      )}
    </div>
  );
}
