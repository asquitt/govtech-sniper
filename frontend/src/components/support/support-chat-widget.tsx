"use client";

import React, { useState } from "react";
import { usePathname } from "next/navigation";
import { MessageCircle, Send, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { supportApi } from "@/lib/api";

export function SupportChatWidget() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (pathname === "/help") {
    return null;
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!message.trim()) return;
    setLoading(true);
    try {
      const response = await supportApi.chat({
        message: message.trim(),
        current_route: pathname,
      });
      setReply(response.reply);
      setMessage("");
    } catch {
      setReply("Support chat is unavailable right now.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-5 left-5 z-40">
      {open ? (
        <div className="w-80 rounded-lg border border-border bg-card p-3 shadow-lg">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-semibold">Support Chat</p>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
          <form className="space-y-2" onSubmit={handleSubmit}>
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Ask a quick question..."
              className="min-h-20 w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
            />
            <div className="flex justify-end">
              <Button size="sm" type="submit" disabled={loading || !message.trim()}>
                <Send className="mr-1 h-3.5 w-3.5" />
                Ask
              </Button>
            </div>
          </form>
          {reply && <p className="mt-2 rounded-md bg-muted p-2 text-xs text-muted-foreground">{reply}</p>}
        </div>
      ) : (
        <Button onClick={() => setOpen(true)} className="rounded-full shadow-md">
          <MessageCircle className="mr-1 h-4 w-4" />
          Support
        </Button>
      )}
    </div>
  );
}
