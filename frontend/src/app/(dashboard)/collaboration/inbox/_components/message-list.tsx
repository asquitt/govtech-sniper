"use client";

import React from "react";
import { Mail, MailOpen, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { InboxMessage, InboxListResponse } from "@/types";
import { MessageTypeBadge } from "./message-type-helpers";

export interface MessageListProps {
  inbox: InboxListResponse | null;
  loading: boolean;
  page: number;
  totalPages: number;
  onSelectMessage: (message: InboxMessage) => void;
  onPageChange: (page: number) => void;
}

export function MessageList({
  inbox,
  loading,
  page,
  totalPages,
  onSelectMessage,
  onPageChange,
}: MessageListProps) {
  if (loading) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Loading messages...
        </CardContent>
      </Card>
    );
  }

  if (inbox && inbox.items.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          <MailOpen className="w-10 h-10 mx-auto mb-3 opacity-50" />
          <p>No messages yet. Send the first message to this workspace.</p>
        </CardContent>
      </Card>
    );
  }

  if (!inbox || inbox.items.length === 0) return null;

  return (
    <>
      <div className="space-y-1">
        {inbox.items.map((msg) => (
          <button
            key={msg.id}
            onClick={() => onSelectMessage(msg)}
            className={`w-full text-left px-4 py-3 rounded-md border transition-colors hover:bg-accent/50 flex items-start gap-3 ${
              msg.is_read ? "bg-background" : "bg-accent/20 border-primary/20"
            }`}
          >
            <div className="mt-0.5">
              {msg.is_read ? (
                <MailOpen className="w-4 h-4 text-muted-foreground" />
              ) : (
                <Mail className="w-4 h-4 text-primary" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span
                  className={`text-sm truncate ${
                    msg.is_read ? "font-normal" : "font-semibold"
                  }`}
                >
                  {msg.subject}
                </span>
                <MessageTypeBadge type={msg.message_type} />
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">
                {msg.sender_name ?? msg.sender_email ?? `User #${msg.sender_id}`}
                {" "}&middot;{" "}
                {new Date(msg.created_at).toLocaleDateString()}
              </div>
            </div>
          </button>
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages} ({inbox.total} messages)
          </span>
          <div className="flex gap-1">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
            >
              <ChevronLeft className="w-3 h-3" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
            >
              <ChevronRight className="w-3 h-3" />
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
