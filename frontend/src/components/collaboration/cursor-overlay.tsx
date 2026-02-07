"use client";

import React from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { CursorPosition } from "@/types";

interface CursorOverlayProps {
  /** Only show cursors for the given section. */
  sectionId: number;
  /** All active cursors (from useCursorPresence). */
  cursors: Map<number, CursorPosition>;
  /** Current user id — to skip rendering own cursor. */
  currentUserId: number;
}

/**
 * Renders colored cursor indicators for collaborators editing the same section.
 * Displayed as small avatar dots at the section header level.
 */
export function CursorOverlay({ sectionId, cursors, currentUserId }: CursorOverlayProps) {
  const sectionCursors = Array.from(cursors.values()).filter(
    (c) => c.section_id === sectionId && c.user_id !== currentUserId
  );

  if (sectionCursors.length === 0) return null;

  return (
    <TooltipProvider delayDuration={0}>
      <div className="flex items-center gap-0.5">
        {sectionCursors.map((cursor) => (
          <Tooltip key={cursor.user_id}>
            <TooltipTrigger asChild>
              <div
                className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white shrink-0"
                style={{ backgroundColor: cursor.color }}
              >
                {cursor.user_name.charAt(0).toUpperCase()}
              </div>
            </TooltipTrigger>
            <TooltipContent side="top" className="text-xs">
              {cursor.user_name}
            </TooltipContent>
          </Tooltip>
        ))}
      </div>
    </TooltipProvider>
  );
}
