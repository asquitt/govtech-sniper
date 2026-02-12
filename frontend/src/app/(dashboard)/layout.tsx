"use client";

import React, { useState } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { GlobalSearch } from "@/components/layout/global-search";
import { SupportChatWidget } from "@/components/support/support-chat-widget";
import { cn } from "@/lib/utils";
import { useRequireAuth } from "@/contexts/auth-context";
import { Loader2 } from "lucide-react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const { isLoading, isAuthenticated } = useRequireAuth();

  // Show loading while checking auth
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  // Don't render dashboard if not authenticated (redirect happens in hook)
  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      <main
        className={cn(
          "flex-1 flex flex-col overflow-hidden transition-all duration-300"
        )}
      >
        {children}
      </main>
      <GlobalSearch />
      <SupportChatWidget />
    </div>
  );
}
