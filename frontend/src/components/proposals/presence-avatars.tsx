"use client";

import React from "react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { DocumentPresenceUser } from "@/types";

const COLORS = [
  "bg-blue-500",
  "bg-green-500",
  "bg-purple-500",
  "bg-orange-500",
  "bg-pink-500",
  "bg-teal-500",
  "bg-indigo-500",
  "bg-rose-500",
];

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function getColor(userId: number): string {
  return COLORS[userId % COLORS.length];
}

interface PresenceAvatarsProps {
  users: DocumentPresenceUser[];
  currentUserId?: number;
  maxVisible?: number;
  className?: string;
}

export function PresenceAvatars({
  users,
  currentUserId,
  maxVisible = 5,
  className,
}: PresenceAvatarsProps) {
  const otherUsers = users.filter((u) => u.user_id !== currentUserId);

  if (otherUsers.length === 0) return null;

  const visible = otherUsers.slice(0, maxVisible);
  const overflow = otherUsers.length - maxVisible;

  return (
    <TooltipProvider delayDuration={0}>
      <div className={cn("flex items-center -space-x-2", className)}>
        {visible.map((user) => (
          <Tooltip key={user.user_id}>
            <TooltipTrigger asChild>
              <div
                className={cn(
                  "flex items-center justify-center w-8 h-8 rounded-full border-2 border-background text-xs font-medium text-white",
                  getColor(user.user_id)
                )}
              >
                {getInitials(user.user_name)}
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <p>{user.user_name}</p>
              <p className="text-xs text-muted-foreground">Editing</p>
            </TooltipContent>
          </Tooltip>
        ))}
        {overflow > 0 && (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center justify-center w-8 h-8 rounded-full border-2 border-background bg-muted text-xs font-medium text-muted-foreground">
                +{overflow}
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              {otherUsers.slice(maxVisible).map((u) => (
                <p key={u.user_id}>{u.user_name}</p>
              ))}
            </TooltipContent>
          </Tooltip>
        )}
        <span className="ml-3 text-xs text-muted-foreground">
          {otherUsers.length} collaborator{otherUsers.length !== 1 ? "s" : ""}
        </span>
      </div>
    </TooltipProvider>
  );
}
