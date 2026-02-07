"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { UserCheck, UserX } from "lucide-react";

interface SectionAssigneeProps {
  assignedToUserId?: number | null;
  assignedAt?: string | null;
  /** Display name of the assigned user (resolved by parent). */
  assignedUserName?: string | null;
  onAssign: (userId: number | null) => void;
  /** Current user id to allow self-assignment. */
  currentUserId: number;
}

/**
 * Displays the current section assignee with assign/unassign buttons.
 */
export function SectionAssignee({
  assignedToUserId,
  assignedAt,
  assignedUserName,
  onAssign,
  currentUserId,
}: SectionAssigneeProps) {
  if (assignedToUserId) {
    const isMe = assignedToUserId === currentUserId;
    return (
      <div className="flex items-center gap-1.5">
        <Badge variant="secondary" className="text-xs flex items-center gap-1">
          <UserCheck className="w-3 h-3" />
          {assignedUserName ?? (isMe ? "You" : `User #${assignedToUserId}`)}
        </Badge>
        {assignedAt && (
          <span className="text-[10px] text-muted-foreground">
            {new Date(assignedAt).toLocaleDateString()}
          </span>
        )}
        <Button
          size="sm"
          variant="ghost"
          className="h-5 px-1"
          onClick={() => onAssign(null)}
          title="Unassign"
        >
          <UserX className="w-3 h-3" />
        </Button>
      </div>
    );
  }

  return (
    <Button
      size="sm"
      variant="ghost"
      className="h-6 text-xs text-muted-foreground"
      onClick={() => onAssign(currentUserId)}
    >
      <UserCheck className="w-3 h-3 mr-1" />
      Assign to me
    </Button>
  );
}
