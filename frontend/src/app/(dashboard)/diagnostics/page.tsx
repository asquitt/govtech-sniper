"use client";

import React, { useEffect, useRef, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { diagnosticsApi } from "@/lib/api";
import { createWebSocket, tokenManager } from "@/lib/api/client";
import type {
  CursorPosition,
  DocumentPresenceUser,
  SectionLock,
  WebSocketDiagnosticsSnapshot,
} from "@/types";

type SocketStatus = "connecting" | "connected" | "disconnected" | "error";

interface SocketEvent {
  type: string;
  timestamp: string;
  detail?: string;
}

const EVENT_FILTER_OPTIONS = [
  "all",
  "connected",
  "task_status",
  "task_update",
  "presence_update",
  "lock_acquired",
  "lock_denied",
  "lock_released",
  "cursor_update",
  "ping",
  "pong",
] as const;

export default function DiagnosticsPage() {
  const wsRef = useRef<WebSocket | null>(null);
  const [socketStatus, setSocketStatus] = useState<SocketStatus>("connecting");
  const [lastTaskStatus, setLastTaskStatus] = useState<string>("unknown");
  const [lastMessageType, setLastMessageType] = useState<string>("none");
  const [events, setEvents] = useState<SocketEvent[]>([]);
  const [connectionNonce, setConnectionNonce] = useState(0);
  const [manualReconnects, setManualReconnects] = useState(0);
  const [eventFilter, setEventFilter] = useState<(typeof EVENT_FILTER_OPTIONS)[number]>("all");
  const [proposalId, setProposalId] = useState("101");
  const [sectionId, setSectionId] = useState("1");
  const [participantName, setParticipantName] = useState("Diagnostics User");
  const [presenceUsers, setPresenceUsers] = useState<DocumentPresenceUser[]>([]);
  const [locks, setLocks] = useState<SectionLock[]>([]);
  const [cursors, setCursors] = useState<CursorPosition[]>([]);
  const [telemetry, setTelemetry] = useState<WebSocketDiagnosticsSnapshot | null>(
    null
  );
  const [diagnosticsTaskId, setDiagnosticsTaskId] = useState(
    () => `diagnostic-task-${Date.now()}`
  );

  useEffect(() => {
    setDiagnosticsTaskId(`diagnostic-task-${Date.now()}`);
  }, [connectionNonce]);

  const addEvent = (type: string, detail?: string) => {
    setEvents((previous) => [
      {
        type,
        timestamp: new Date().toISOString(),
        detail,
      },
      ...previous.slice(0, 49),
    ]);
  };

  const sendMessage = (payload: Record<string, unknown>) => {
    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      addEvent("send_failed", "WebSocket is not connected.");
      return;
    }
    socket.send(JSON.stringify(payload));
  };

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const snapshot = await diagnosticsApi.getWebsocketTelemetry();
        if (mounted) {
          setTelemetry(snapshot);
        }
      } catch {
        if (mounted) {
          setTelemetry(null);
        }
      }
    };
    void poll();
    const timer = window.setInterval(() => {
      void poll();
    }, 3000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, [connectionNonce]);

  useEffect(() => {
    const accessToken = tokenManager.getAccessToken();
    if (!accessToken) {
      setSocketStatus("error");
      setEvents([
        {
          type: "auth_missing",
          timestamp: new Date().toISOString(),
          detail: "No access token found.",
        },
      ]);
      return;
    }

    setSocketStatus("connecting");
    setEvents([]);
    setLastTaskStatus("unknown");
    setLastMessageType("none");
    setPresenceUsers([]);
    setLocks([]);
    setCursors([]);

    const socket = createWebSocket(accessToken);
    wsRef.current = socket;

    socket.onopen = () => {
      setSocketStatus("connected");
      socket.send(JSON.stringify({ type: "ping" }));
      socket.send(
        JSON.stringify({
          type: "watch_task",
          task_id: diagnosticsTaskId,
        })
      );
      addEvent("connected", `Watching ${diagnosticsTaskId}`);
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as {
          type?: string;
          status?: string;
          task_id?: string;
          users?: DocumentPresenceUser[];
          locks?: SectionLock[];
          cursors?: CursorPosition[];
          user_name?: string;
          section_id?: number;
        };
        const messageType = payload.type || "unknown";
        setLastMessageType(messageType);
        if (
          (messageType === "task_status" || messageType === "task_update") &&
          payload.status
        ) {
          setLastTaskStatus(payload.status);
        }
        if (messageType === "presence_update") {
          setPresenceUsers(payload.users || []);
          setLocks(payload.locks || []);
          setCursors(payload.cursors || []);
        }
        if (messageType === "lock_acquired" && payload.section_id) {
          addEvent(
            messageType,
            `section ${payload.section_id} locked by ${payload.user_name || "unknown"}`
          );
          return;
        }
        if (messageType === "lock_denied") {
          addEvent(messageType, "Lock denied for selected section.");
          return;
        }
        addEvent(
          messageType,
          payload.task_id ? `task: ${payload.task_id}` : undefined
        );
      } catch {
        setLastMessageType("parse_error");
      }
    };

    socket.onerror = () => {
      setSocketStatus("error");
    };

    socket.onclose = () => {
      setSocketStatus((current) => (current === "error" ? current : "disconnected"));
    };

    return () => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "unwatch_task", task_id: diagnosticsTaskId }));
      }
      socket.close();
    };
  }, [diagnosticsTaskId]);

  const filteredEvents =
    eventFilter === "all" ? events : events.filter((event) => event.type === eventFilter);

  const parsedProposalId = Number(proposalId) || 0;
  const parsedSectionId = Number(sectionId) || 0;

  const statusVariant =
    socketStatus === "connected"
      ? "success"
      : socketStatus === "connecting"
        ? "secondary"
        : socketStatus === "error"
          ? "destructive"
          : "outline";

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Diagnostics"
        description="Runtime and real-time capability diagnostics"
        actions={
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setManualReconnects((count) => count + 1);
              setConnectionNonce((n) => n + 1);
            }}
          >
            Reconnect WebSocket
          </Button>
        }
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        <Card className="border border-border">
          <CardHeader>
            <CardTitle>WebSocket Task Feed</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-sm">
              <div className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">Connection status</p>
                <Badge className="mt-1" variant={statusVariant}>
                  {socketStatus}
                </Badge>
              </div>
              <div className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">Last message</p>
                <p className="mt-1 font-medium">{lastMessageType}</p>
              </div>
              <div className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">Task status</p>
                <p className="mt-1 font-medium">{lastTaskStatus}</p>
              </div>
              <div className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">Presence telemetry</p>
                <p className="mt-1 font-medium">
                  {presenceUsers.length} users / {locks.length} locks / {cursors.length} cursors
                </p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Active probe task id: <span className="font-mono">{diagnosticsTaskId}</span>
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
              <div className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">Task-watch latency</p>
                <p className="mt-1 font-medium" data-testid="telemetry-task-latency">
                  {telemetry?.task_watch.avg_status_latency_ms != null
                    ? `${telemetry.task_watch.avg_status_latency_ms}ms avg / ${telemetry.task_watch.p95_status_latency_ms ?? "n/a"}ms p95`
                    : "n/a"}
                </p>
              </div>
              <div className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">Reconnect counts</p>
                <p className="mt-1 font-medium" data-testid="telemetry-reconnect-count">
                  server {telemetry?.connections.reconnect_count ?? 0} / local{" "}
                  {manualReconnects}
                </p>
              </div>
              <div className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">Event throughput</p>
                <p className="mt-1 font-medium" data-testid="telemetry-throughput">
                  in {telemetry?.event_throughput.inbound_events_per_minute ?? 0}/min, out{" "}
                  {telemetry?.event_throughput.outbound_events_per_minute ?? 0}/min
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-border">
          <CardHeader>
            <CardTitle>Collaborative Probe</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
              <label className="text-xs text-muted-foreground">
                Proposal ID
                <input
                  className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                  value={proposalId}
                  onChange={(event) => setProposalId(event.target.value)}
                />
              </label>
              <label className="text-xs text-muted-foreground">
                Section ID
                <input
                  className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                  value={sectionId}
                  onChange={(event) => setSectionId(event.target.value)}
                />
              </label>
              <label className="text-xs text-muted-foreground">
                User label
                <input
                  className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                  value={participantName}
                  onChange={(event) => setParticipantName(event.target.value)}
                />
              </label>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  sendMessage({
                    type: "join_document",
                    proposal_id: parsedProposalId,
                    user_name: participantName,
                  })
                }
              >
                Join Document
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  sendMessage({
                    type: "leave_document",
                    proposal_id: parsedProposalId,
                  })
                }
              >
                Leave Document
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  sendMessage({
                    type: "lock_section",
                    proposal_id: parsedProposalId,
                    section_id: parsedSectionId,
                    user_name: participantName,
                  })
                }
              >
                Lock Section
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  sendMessage({
                    type: "unlock_section",
                    proposal_id: parsedProposalId,
                    section_id: parsedSectionId,
                  })
                }
              >
                Unlock Section
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  sendMessage({
                    type: "cursor_update",
                    proposal_id: parsedProposalId,
                    section_id: parsedSectionId,
                    user_name: participantName,
                    position: Math.floor(Math.random() * 1000),
                  })
                }
              >
                Send Cursor
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <div className="rounded-md border border-border p-3 space-y-1">
                <p className="font-medium text-foreground">Presence Users</p>
                {presenceUsers.length === 0 ? (
                  <p className="text-muted-foreground">No users joined.</p>
                ) : (
                  presenceUsers.map((user) => (
                    <p key={user.user_id} className="text-muted-foreground">
                      {user.user_name} ({user.user_id})
                    </p>
                  ))
                )}
              </div>
              <div className="rounded-md border border-border p-3 space-y-1">
                <p className="font-medium text-foreground">Section Locks</p>
                {locks.length === 0 ? (
                  <p className="text-muted-foreground">No active locks.</p>
                ) : (
                  locks.map((lock) => (
                    <p key={`${lock.section_id}-${lock.user_id}`} className="text-muted-foreground">
                      Section {lock.section_id} by {lock.user_name}
                    </p>
                  ))
                )}
              </div>
              <div className="rounded-md border border-border p-3 space-y-1">
                <p className="font-medium text-foreground">Cursor Telemetry</p>
                {cursors.length === 0 ? (
                  <p className="text-muted-foreground">No cursor updates.</p>
                ) : (
                  cursors.map((cursor) => (
                    <p
                      key={`${cursor.user_id}-${cursor.section_id ?? "none"}`}
                      className="text-muted-foreground"
                    >
                      {cursor.user_name} @ section {cursor.section_id ?? "-"} pos {cursor.position}
                    </p>
                  ))
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-border">
          <CardHeader>
            <div className="flex items-center justify-between gap-2">
              <CardTitle>Recent Events</CardTitle>
              <select
                aria-label="Event filter"
                className="rounded-md border border-border bg-background px-2 py-1 text-xs"
                value={eventFilter}
                onChange={(event) =>
                  setEventFilter(event.target.value as (typeof EVENT_FILTER_OPTIONS)[number])
                }
              >
                {EVENT_FILTER_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
          </CardHeader>
          <CardContent>
            {filteredEvents.length === 0 ? (
              <p className="text-sm text-muted-foreground">No events captured yet.</p>
            ) : (
              <div className="space-y-2">
                {filteredEvents.map((item, index) => (
                  <div
                    key={`${item.timestamp}-${item.type}-${index}`}
                    className="rounded-md border border-border px-3 py-2 text-xs"
                  >
                    <p className="font-medium">{item.type}</p>
                    <p className="text-muted-foreground">{new Date(item.timestamp).toLocaleString()}</p>
                    {item.detail ? <p className="text-muted-foreground">{item.detail}</p> : null}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
