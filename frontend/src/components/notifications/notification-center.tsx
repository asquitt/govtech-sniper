"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Bell, CheckCheck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { notificationApi } from "@/lib/api";
import type { Notification } from "@/lib/api";
import api from "@/lib/api/client";

const TYPE_ICONS: Record<string, string> = {
  deadline_reminder: "🕐",
  rfp_match: "🎯",
  analysis_complete: "📊",
  generation_complete: "📝",
  system_alert: "⚠️",
  team_invite: "👥",
  comment_added: "💬",
  mention: "@",
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 60) return `${min}m`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h`;
  return `${Math.floor(hr / 24)}d`;
}

export function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchNotifications = useCallback(async () => {
    try {
      const items = await notificationApi.list({ limit: 20 });
      setNotifications(Array.isArray(items) ? items : []);

      const { data } = await api.get("/notifications/unread-count");
      setUnreadCount(data?.unread_count ?? 0);
    } catch {
      // Silently fail if not authed
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  const handleMarkRead = async (id: number) => {
    try {
      await notificationApi.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // ignore
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationApi.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // ignore
    }
  };

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        onClick={() => setOpen(!open)}
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-destructive text-[10px] font-bold text-white flex items-center justify-center">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </Button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />

          <div className="absolute right-0 top-10 z-50 w-80 bg-card border border-border rounded-lg shadow-xl">
            <div className="flex items-center justify-between p-3 border-b border-border">
              <span className="text-sm font-medium text-foreground">Notifications</span>
              <div className="flex gap-1">
                {unreadCount > 0 && (
                  <Button variant="ghost" size="sm" onClick={handleMarkAllRead} className="h-7 text-xs">
                    <CheckCheck className="h-3.5 w-3.5 mr-1" />
                    Read all
                  </Button>
                )}
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setOpen(false)}>
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>

            <div className="max-h-80 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="p-6 text-center text-sm text-muted-foreground">
                  No notifications yet
                </div>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    className={cn(
                      "flex items-start gap-2 p-3 border-b border-border/50 hover:bg-muted/30 cursor-pointer",
                      !n.is_read && "bg-primary/5"
                    )}
                    onClick={() => !n.is_read && handleMarkRead(n.id)}
                  >
                    <span className="text-base mt-0.5">
                      {TYPE_ICONS[n.type] || "📌"}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-foreground truncate">
                        {n.title}
                      </p>
                      <p className="text-[11px] text-muted-foreground line-clamp-2">
                        {n.message}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1 shrink-0">
                      <span className="text-[10px] text-muted-foreground">
                        {timeAgo(n.created_at)}
                      </span>
                      {!n.is_read && (
                        <div className="w-2 h-2 rounded-full bg-primary" />
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
