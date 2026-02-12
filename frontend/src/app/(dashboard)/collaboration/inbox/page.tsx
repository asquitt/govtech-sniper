"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Inbox,
  Send,
  Mail,
  MailOpen,
  Trash2,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  Bell,
  Forward,
} from "lucide-react";
import { collaborationApi } from "@/lib/api";
import type {
  InboxMessage,
  InboxListResponse,
  SharedWorkspace,
  InboxMessageType,
} from "@/types";

// ---------------------------------------------------------------------------
// Message type badge
// ---------------------------------------------------------------------------

function MessageTypeBadge({ type }: { type: InboxMessageType }) {
  const config: Record<InboxMessageType, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
    general: { label: "General", variant: "secondary" },
    opportunity_alert: { label: "Opportunity", variant: "default" },
    rfp_forward: { label: "RFP Forward", variant: "outline" },
  };
  const { label, variant } = config[type] ?? config.general;
  return <Badge variant={variant}>{label}</Badge>;
}

function MessageTypeIcon({ type }: { type: InboxMessageType }) {
  switch (type) {
    case "opportunity_alert":
      return <Bell className="w-4 h-4 text-blue-500" />;
    case "rfp_forward":
      return <Forward className="w-4 h-4 text-purple-500" />;
    default:
      return <Mail className="w-4 h-4 text-muted-foreground" />;
  }
}

// ---------------------------------------------------------------------------
// Compose modal (inline)
// ---------------------------------------------------------------------------

function ComposeForm({
  onSend,
  onCancel,
  sending,
}: {
  onSend: (subject: string, body: string, messageType: InboxMessageType) => void;
  onCancel: () => void;
  sending: boolean;
}) {
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

// ---------------------------------------------------------------------------
// Message detail
// ---------------------------------------------------------------------------

function MessageDetail({
  message,
  onClose,
  onDelete,
}: {
  message: InboxMessage;
  onClose: () => void;
  onDelete: (id: number) => void;
}) {
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

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function WorkspaceInboxPage() {
  const searchParams = useSearchParams();
  const workspaceIdParam = searchParams.get("workspace");

  const [workspaces, setWorkspaces] = useState<SharedWorkspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<number | null>(null);
  const [inbox, setInbox] = useState<InboxListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [composing, setComposing] = useState(false);
  const [sending, setSending] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState<InboxMessage | null>(null);

  // Load workspaces on mount
  useEffect(() => {
    collaborationApi.listWorkspaces().then((ws) => {
      setWorkspaces(ws);
      if (workspaceIdParam) {
        const id = parseInt(workspaceIdParam, 10);
        if (ws.some((w) => w.id === id)) {
          setSelectedWorkspaceId(id);
        }
      } else if (ws.length > 0 && !selectedWorkspaceId) {
        setSelectedWorkspaceId(ws[0].id);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchInbox = useCallback(async () => {
    if (!selectedWorkspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await collaborationApi.listInboxMessages(selectedWorkspaceId, {
        page,
        page_size: 20,
      });
      setInbox(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load inbox";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [selectedWorkspaceId, page]);

  useEffect(() => {
    fetchInbox();
  }, [fetchInbox]);

  const handleSend = async (subject: string, body: string, messageType: InboxMessageType) => {
    if (!selectedWorkspaceId) return;
    setSending(true);
    try {
      await collaborationApi.sendInboxMessage(selectedWorkspaceId, {
        subject,
        body,
        message_type: messageType,
      });
      setComposing(false);
      setPage(1);
      await fetchInbox();
    } catch {
      setError("Failed to send message");
    } finally {
      setSending(false);
    }
  };

  const handleMarkRead = async (message: InboxMessage) => {
    if (!selectedWorkspaceId) return;
    setSelectedMessage(message);
    if (!message.is_read) {
      try {
        await collaborationApi.markInboxMessageRead(selectedWorkspaceId, message.id);
        await fetchInbox();
      } catch {
        // Silently fail for read marking
      }
    }
  };

  const handleDelete = async (messageId: number) => {
    if (!selectedWorkspaceId) return;
    try {
      await collaborationApi.deleteInboxMessage(selectedWorkspaceId, messageId);
      setSelectedMessage(null);
      await fetchInbox();
    } catch {
      setError("Failed to delete message");
    }
  };

  const totalPages = inbox ? Math.ceil(inbox.total / inbox.page_size) : 0;
  const currentWorkspace = workspaces.find((w) => w.id === selectedWorkspaceId);

  return (
    <>
      <Header title="Team Inbox" />
      <main className="container mx-auto p-6 max-w-4xl space-y-6">
        {/* Workspace selector */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Inbox className="w-5 h-5 text-muted-foreground" />
            <div>
              <h1 className="text-lg font-semibold">
                {currentWorkspace ? currentWorkspace.name : "Team Inbox"}
              </h1>
              <p className="text-sm text-muted-foreground">
                Shared messages for your workspace
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {workspaces.length > 1 && (
              <select
                className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                value={selectedWorkspaceId ?? ""}
                onChange={(e) => {
                  setSelectedWorkspaceId(Number(e.target.value));
                  setPage(1);
                  setSelectedMessage(null);
                }}
              >
                {workspaces.map((ws) => (
                  <option key={ws.id} value={ws.id}>
                    {ws.name}
                  </option>
                ))}
              </select>
            )}
            <Button size="sm" onClick={() => { setComposing(true); setSelectedMessage(null); }}>
              <Send className="w-3 h-3 mr-1" /> Compose
            </Button>
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 p-3 rounded-md">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {/* No workspace */}
        {!selectedWorkspaceId && !loading && (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              <Inbox className="w-10 h-10 mx-auto mb-3 opacity-50" />
              <p>No workspace selected. Create a workspace in Collaboration to use the team inbox.</p>
            </CardContent>
          </Card>
        )}

        {/* Compose form */}
        {composing && selectedWorkspaceId && (
          <ComposeForm
            onSend={handleSend}
            onCancel={() => setComposing(false)}
            sending={sending}
          />
        )}

        {/* Message detail */}
        {selectedMessage && !composing && (
          <MessageDetail
            message={selectedMessage}
            onClose={() => setSelectedMessage(null)}
            onDelete={handleDelete}
          />
        )}

        {/* Message list */}
        {!selectedMessage && !composing && selectedWorkspaceId && (
          <>
            {loading && (
              <Card>
                <CardContent className="py-8 text-center text-muted-foreground">
                  Loading messages...
                </CardContent>
              </Card>
            )}

            {!loading && inbox && inbox.items.length === 0 && (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground">
                  <MailOpen className="w-10 h-10 mx-auto mb-3 opacity-50" />
                  <p>No messages yet. Send the first message to this workspace.</p>
                </CardContent>
              </Card>
            )}

            {!loading && inbox && inbox.items.length > 0 && (
              <div className="space-y-1">
                {inbox.items.map((msg) => (
                  <button
                    key={msg.id}
                    onClick={() => handleMarkRead(msg)}
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
            )}

            {/* Pagination */}
            {!loading && inbox && totalPages > 1 && (
              <div className="flex items-center justify-between pt-2">
                <span className="text-sm text-muted-foreground">
                  Page {page} of {totalPages} ({inbox.total} messages)
                </span>
                <div className="flex gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    <ChevronLeft className="w-3 h-3" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    <ChevronRight className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </>
  );
}
