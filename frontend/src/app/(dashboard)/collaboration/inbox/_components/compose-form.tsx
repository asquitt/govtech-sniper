"use client";

import React, { useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { InboxMessageType } from "@/types";

export interface ComposeFormProps {
  onSend: (subject: string, body: string, messageType: InboxMessageType) => void;
  onCancel: () => void;
  sending: boolean;
}

export function ComposeForm({ onSend, onCancel, sending }: ComposeFormProps) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [messageType, setMessageType] = useState<InboxMessageType>("general");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !body.trim()) return;
    onSend(subject.trim(), body.trim(), messageType);
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">New Message</CardTitle>
        <CardDescription>Send a message to the workspace inbox</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-sm font-medium text-foreground">Type</label>
            <select
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={messageType}
              onChange={(e) => setMessageType(e.target.value as InboxMessageType)}
            >
              <option value="general">General</option>
              <option value="opportunity_alert">Opportunity Alert</option>
              <option value="rfp_forward">RFP Forward</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-foreground">Subject</label>
            <input
              type="text"
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="Message subject..."
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground">Body</label>
            <textarea
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[100px]"
              placeholder="Write your message..."
              value={body}
              onChange={(e) => setBody(e.target.value)}
              required
            />
          </div>
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" size="sm" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={sending || !subject.trim() || !body.trim()}>
              <Send className="w-3 h-3 mr-1" />
              {sending ? "Sending..." : "Send"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
