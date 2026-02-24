"use client";

import React from "react";
import { ChevronLeft, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { InboxMessage } from "@/types";
import { MessageTypeBadge, MessageTypeIcon } from "./message-type-helpers";

export interface MessageDetailProps {
  message: InboxMessage;
  onClose: () => void;
  onDelete: (id: number) => void;
}

export function MessageDetail({ message, onClose, onDelete }: MessageDetailProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <MessageTypeIcon type={message.message_type} />
              <CardTitle className="text-base">{message.subject}</CardTitle>
            </div>
            <CardDescription>
              From {message.sender_name ?? message.sender_email ?? `User #${message.sender_id}`}
              {" "}&middot;{" "}
              {new Date(message.created_at).toLocaleString()}
            </CardDescription>
          </div>
          <div className="flex gap-1">
            <MessageTypeBadge type={message.message_type} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="whitespace-pre-wrap text-sm text-foreground">{message.body}</div>
        <div className="flex gap-2 justify-between pt-2 border-t">
          <Button variant="outline" size="sm" onClick={onClose}>
            <ChevronLeft className="w-3 h-3 mr-1" /> Back
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => onDelete(message.id)}
          >
            <Trash2 className="w-3 h-3 mr-1" /> Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
