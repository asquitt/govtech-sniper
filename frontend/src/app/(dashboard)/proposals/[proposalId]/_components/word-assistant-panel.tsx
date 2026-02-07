"use client";

import React from "react";
import { FileText, Plus, RefreshCw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";
import type { WordAddinSession, WordAddinEvent } from "@/types";

interface WordAssistantPanelProps {
  sessions: WordAddinSession[];
  events: Record<number, WordAddinEvent[]>;
  docName: string;
  onDocNameChange: (name: string) => void;
  onCreateSession: () => void;
  onSyncSession: (sessionId: number) => void;
  onLoadEvents: (sessionId: number) => void;
  onUpdateStatus: (sessionId: number, status: WordAddinSession["status"]) => void;
  isSyncing: boolean;
  updatingSessionId: number | null;
}

export function WordAssistantPanel({
  sessions,
  events,
  docName,
  onDocNameChange,
  onCreateSession,
  onSyncSession,
  onLoadEvents,
  onUpdateStatus,
  isSyncing,
  updatingSessionId,
}: WordAssistantPanelProps) {
  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-primary" />
          <p className="text-sm font-semibold">Word Assistant</p>
        </div>
        <div className="space-y-2">
          {sessions.length === 0 ? (
            <p className="text-xs text-muted-foreground">No Word sessions yet.</p>
          ) : (
            sessions.map((session) => (
              <div key={session.id} className="border border-border rounded-md p-2 space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm text-foreground">{session.document_name}</p>
                    <p className="text-xs text-muted-foreground">Status: {session.status}</p>
                    {session.last_synced_at && (
                      <p className="text-xs text-muted-foreground">
                        Last synced {formatDate(session.last_synced_at)}
                      </p>
                    )}
                    {events[session.id] && (
                      <p className="text-xs text-muted-foreground">
                        Events: {events[session.id].length}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-col gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onLoadEvents(session.id)}
                    >
                      History
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => onSyncSession(session.id)}
                      disabled={isSyncing}
                    >
                      <RefreshCw className="w-4 h-4" />
                      Sync
                    </Button>
                  </div>
                </div>
                <div className="grid gap-2 text-xs">
                  <label className="text-muted-foreground">
                    Status
                    <select
                      className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-xs"
                      value={session.status}
                      onChange={(e) =>
                        onUpdateStatus(
                          session.id,
                          e.target.value as WordAddinSession["status"]
                        )
                      }
                      disabled={updatingSessionId === session.id}
                    >
                      <option value="active">Active</option>
                      <option value="paused">Paused</option>
                      <option value="completed">Completed</option>
                    </select>
                  </label>
                </div>
                {events[session.id] && (
                  <div className="rounded-md border border-border bg-background/40 p-2 space-y-1 text-xs">
                    {events[session.id].length === 0 ? (
                      <p className="text-muted-foreground">No events recorded yet.</p>
                    ) : (
                      events[session.id].map((event) => (
                        <div key={event.id} className="flex items-start justify-between gap-2">
                          <div>
                            <p className="text-foreground">{event.event_type}</p>
                            {event.payload && Object.keys(event.payload).length > 0 && (
                              <p className="text-muted-foreground">
                                {JSON.stringify(event.payload)}
                              </p>
                            )}
                          </div>
                          <span className="text-muted-foreground">
                            {formatDate(event.created_at)}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
        <div className="space-y-2">
          <input
            className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Document name"
            value={docName}
            onChange={(e) => onDocNameChange(e.target.value)}
          />
          <Button
            variant="outline"
            className="w-full"
            onClick={onCreateSession}
          >
            <Plus className="w-4 h-4" />
            Create Word Session
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
