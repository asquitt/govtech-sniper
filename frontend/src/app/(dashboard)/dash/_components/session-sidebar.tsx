"use client";

import React from "react";
import { MessageSquarePlus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDashStore } from "@/lib/stores/dash-store";

export function SessionSidebar() {
  const { sessions, activeSessionId, createSession, selectSession, deleteSession } =
    useDashStore();

  return (
    <div className="w-64 border-r border-border flex flex-col h-full bg-background">
      <div className="p-3 border-b border-border">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={() => createSession()}
        >
          <MessageSquarePlus className="w-4 h-4" />
          New Chat
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <p className="text-xs text-muted-foreground p-3">No conversations yet</p>
        ) : (
          <div className="space-y-0.5 p-1">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`group flex items-center gap-1 rounded-md px-2 py-2 cursor-pointer text-sm transition-colors ${
                  session.id === activeSessionId
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                }`}
                onClick={() => selectSession(session.id)}
              >
                <span className="flex-1 truncate">
                  {session.title || "New Chat"}
                </span>
                <button
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-destructive transition-opacity"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteSession(session.id);
                  }}
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
