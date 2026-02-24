"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Inbox, Send, AlertCircle } from "lucide-react";
import { collaborationApi } from "@/lib/api";
import type {
  InboxMessage,
  InboxListResponse,
  SharedWorkspace,
  InboxMessageType,
} from "@/types";
import { ComposeForm } from "./_components/compose-form";
import { MessageDetail } from "./_components/message-detail";
import { MessageList } from "./_components/message-list";

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
          <MessageList
            inbox={inbox}
            loading={loading}
            page={page}
            totalPages={totalPages}
            onSelectMessage={handleMarkRead}
            onPageChange={setPage}
          />
        )}
      </main>
    </>
  );
}
