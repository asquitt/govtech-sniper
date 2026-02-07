"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Edit3,
  Sparkles,
  Calendar,
  CheckCircle,
  MessageSquare,
  CheckCheck,
  UserPlus,
  UserCheck,
  FileDown,
  RefreshCw,
} from "lucide-react";
import type { ActivityFeedEntry, ActivityType } from "@/types";
import { activityApi } from "@/lib/api/activity";

interface ActivityFeedProps {
  proposalId: number;
  /** Auto-refresh interval in ms. 0 = disabled. */
  refreshInterval?: number;
}

const ICON_MAP: Record<ActivityType, React.ElementType> = {
  section_edited: Edit3,
  section_generated: Sparkles,
  review_scheduled: Calendar,
  review_completed: CheckCircle,
  comment_added: MessageSquare,
  comment_resolved: CheckCheck,
  member_joined: UserPlus,
  section_assigned: UserCheck,
  document_exported: FileDown,
  status_changed: RefreshCw,
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function ActivityFeed({ proposalId, refreshInterval = 15_000 }: ActivityFeedProps) {
  const [entries, setEntries] = useState<ActivityFeedEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await activityApi.list(proposalId, { limit: 50 });
      setEntries(data);
    } catch (err) {
      console.error("Failed to load activity feed:", err);
    } finally {
      setLoading(false);
    }
  }, [proposalId]);

  useEffect(() => {
    load();
    if (refreshInterval > 0) {
      const id = setInterval(load, refreshInterval);
      return () => clearInterval(id);
    }
  }, [load, refreshInterval]);

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Activity</CardTitle>
      </CardHeader>
      <CardContent className="overflow-y-auto max-h-[500px] space-y-3">
        {loading && entries.length === 0 ? (
          <p className="text-xs text-muted-foreground">Loading...</p>
        ) : entries.length === 0 ? (
          <p className="text-xs text-muted-foreground">No activity yet.</p>
        ) : (
          entries.map((entry) => {
            const Icon = ICON_MAP[entry.activity_type] ?? RefreshCw;
            return (
              <div key={entry.id} className="flex gap-2 items-start">
                <div className="mt-0.5 p-1 rounded bg-muted">
                  <Icon className="w-3.5 h-3.5 text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs leading-snug">{entry.summary}</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <Badge variant="secondary" className="text-[10px] px-1 py-0">
                      {entry.activity_type.replace(/_/g, " ")}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground">
                      {relativeTime(entry.created_at)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}
