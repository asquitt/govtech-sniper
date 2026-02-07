"use client";

import React from "react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import type { ReviewComment } from "@/types";

interface InlineCommentMarkerProps {
  comment: ReviewComment;
  children: React.ReactNode;
}

/**
 * Wraps highlighted text with a popover showing the inline comment.
 */
export function InlineCommentMarker({ comment, children }: InlineCommentMarkerProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <span className="bg-yellow-200/50 dark:bg-yellow-900/30 cursor-pointer border-b border-yellow-500 border-dashed">
          {children}
        </span>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-3 space-y-2">
        <div className="flex items-center gap-1.5">
          <Badge variant="secondary" className="text-xs">
            {comment.severity}
          </Badge>
          <Badge
            variant={
              comment.status === "open"
                ? "warning"
                : comment.status === "rejected"
                  ? "destructive"
                  : "success"
            }
            className="text-xs"
          >
            {comment.status}
          </Badge>
        </div>
        <p className="text-sm">{comment.comment_text}</p>
        {comment.anchor_text && (
          <p className="text-xs text-muted-foreground italic truncate">
            &ldquo;{comment.anchor_text}&rdquo;
          </p>
        )}
        <p className="text-[10px] text-muted-foreground">
          {new Date(comment.created_at).toLocaleString()}
        </p>
      </PopoverContent>
    </Popover>
  );
}
