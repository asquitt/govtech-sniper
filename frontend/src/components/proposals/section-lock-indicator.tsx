"use client";

import React from "react";
import { Lock, Unlock } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import type { SectionLock } from "@/types";

interface SectionLockIndicatorProps {
  lock: SectionLock | null;
  currentUserId?: number;
  onLock?: () => void;
  onUnlock?: () => void;
  className?: string;
}

export function SectionLockIndicator({
  lock,
  currentUserId,
  onLock,
  onUnlock,
  className,
}: SectionLockIndicatorProps) {
  const isLockedByMe = lock && lock.user_id === currentUserId;
  const isLockedByOther = lock && lock.user_id !== currentUserId;

  if (isLockedByOther) {
    return (
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className={cn(
                "flex items-center gap-1.5 px-2 py-1 rounded-md bg-destructive/10 text-destructive text-xs",
                className
              )}
            >
              <Lock className="w-3 h-3" />
              <span>Locked by {lock.user_name}</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>{lock.user_name} is currently editing this section</p>
            <p className="text-xs text-muted-foreground">
              Since {new Date(lock.locked_at).toLocaleTimeString()}
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  if (isLockedByMe) {
    return (
      <Button
        variant="ghost"
        size="sm"
        onClick={onUnlock}
        className={cn("gap-1.5 text-xs text-primary h-7", className)}
      >
        <Lock className="w-3 h-3" />
        <span>Editing (click to release)</span>
      </Button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={onLock}
      className={cn("gap-1.5 text-xs text-muted-foreground h-7", className)}
    >
      <Unlock className="w-3 h-3" />
      <span>Click to edit</span>
    </Button>
  );
}
