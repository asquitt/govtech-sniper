"use client";

import React, { useEffect } from "react";
import { Header } from "@/components/layout/header";
import { useDashStore } from "@/lib/stores/dash-store";
import { SessionSidebar } from "./_components/session-sidebar";
import { ContextSelector } from "./_components/context-selector";
import { ChatPanel } from "./_components/chat-panel";

export default function DashPage() {
  const loadSessions = useDashStore((s) => s.loadSessions);

  useEffect(() => {
    loadSessions();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex h-full">
      <SessionSidebar />
      <div className="flex-1 flex flex-col min-h-0">
        <Header title="Dash" description="Your AI assistant for GovCon workflows" />
        <ContextSelector />
        <ChatPanel />
      </div>
    </div>
  );
}
