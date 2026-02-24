"use client";

import React, { useEffect, useRef, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { diagnosticsApi } from "@/lib/api";
import { createWebSocket, tokenManager } from "@/lib/api/client";
import type {
  CursorPosition,
  DocumentPresenceUser,
  SectionLock,
  WebSocketDiagnosticsAlertSnapshot,
  WebSocketDiagnosticsThresholds,
  WebSocketDiagnosticsSnapshot,
} from "@/types";
import { WebSocketTaskFeed } from "./_components/WebSocketTaskFeed";
import { CollaborativeProbe } from "./_components/CollaborativeProbe";
import { RecentEvents } from "./_components/RecentEvents";

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
  const [alertSnapshot, setAlertSnapshot] =
    useState<WebSocketDiagnosticsAlertSnapshot | null>(null);
  const [alertThresholds, setAlertThresholds] = useState<WebSocketDiagnosticsThresholds>({
    max_avg_status_latency_ms: 2000,
    max_p95_status_latency_ms: 5000,
    max_reconnect_count: 25,
    max_disconnect_ratio: 0.4,
    min_outbound_events_per_minute: 1,
    min_active_connection_count: 0,
  });
  const [isEvaluatingAlerts, setIsEvaluatingAlerts] = useState(false);
  const [isExportingTelemetry, setIsExportingTelemetry] = useState(false);
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

  const fetchAlerts = React.useCallback(async () => {
    setIsEvaluatingAlerts(true);
    try {
      const snapshot = await diagnosticsApi.getWebsocketAlerts({
        ...alertThresholds,
        include_all: true,
      });
      setAlertSnapshot(snapshot);
    } catch {
      setAlertSnapshot(null);
    } finally {
      setIsEvaluatingAlerts(false);
    }
  }, [alertThresholds]);

  useEffect(() => {
    void fetchAlerts();
  }, [fetchAlerts, connectionNonce]);

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

  const statusVariant =
    socketStatus === "connected"
      ? "success"
      : socketStatus === "connecting"
        ? "secondary"
        : socketStatus === "error"
          ? "destructive"
          : "outline";

  const handleExportTelemetry = async () => {
    setIsExportingTelemetry(true);
    try {
      const blob = await diagnosticsApi.exportWebsocketTelemetryCsv({
        ...alertThresholds,
        include_alerts: true,
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "websocket_diagnostics.csv";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } finally {
      setIsExportingTelemetry(false);
    }
  };

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
        <WebSocketTaskFeed
          socketStatus={socketStatus}
          statusVariant={statusVariant}
          lastMessageType={lastMessageType}
          lastTaskStatus={lastTaskStatus}
          presenceCount={presenceUsers.length}
          lockCount={locks.length}
          cursorCount={cursors.length}
          diagnosticsTaskId={diagnosticsTaskId}
          telemetry={telemetry}
          manualReconnects={manualReconnects}
          alertThresholds={alertThresholds}
          onAlertThresholdsChange={setAlertThresholds}
          alertSnapshot={alertSnapshot}
          isEvaluatingAlerts={isEvaluatingAlerts}
          isExportingTelemetry={isExportingTelemetry}
          onEvaluateAlerts={() => void fetchAlerts()}
          onExportTelemetry={() => void handleExportTelemetry()}
        />

        <CollaborativeProbe
          proposalId={proposalId}
          sectionId={sectionId}
          participantName={participantName}
          onProposalIdChange={setProposalId}
          onSectionIdChange={setSectionId}
          onParticipantNameChange={setParticipantName}
          onSendMessage={sendMessage}
          presenceUsers={presenceUsers}
          locks={locks}
          cursors={cursors}
        />

        <RecentEvents
          events={filteredEvents}
          eventFilter={eventFilter}
          filterOptions={EVENT_FILTER_OPTIONS}
          onFilterChange={(value) =>
            setEventFilter(value as (typeof EVENT_FILTER_OPTIONS)[number])
          }
        />
      </div>
    </div>
  );
}
