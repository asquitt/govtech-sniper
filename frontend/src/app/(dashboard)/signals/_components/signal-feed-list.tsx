"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SignalType } from "@/types/signals";

interface Signal {
  id: number;
  signal_type: SignalType;
  title: string;
  agency?: string | null;
  relevance_score: number;
  source_url?: string | null;
  is_read: boolean;
}

const SIGNAL_TYPE_LABELS: Record<SignalType, string> = {
  budget: "Budget",
  award: "Award",
  news: "News",
  congressional: "Congressional",
  recompete: "Recompete",
};

const SIGNAL_TYPE_COLORS: Record<SignalType, string> = {
  budget: "bg-green-500/10 text-green-600",
  award: "bg-blue-500/10 text-blue-600",
  news: "bg-yellow-500/10 text-yellow-600",
  congressional: "bg-purple-500/10 text-purple-600",
  recompete: "bg-orange-500/10 text-orange-600",
};

export interface SignalFeedListProps {
  signals: Signal[];
  loading: boolean;
  onMarkRead: (id: number) => void;
}

export function SignalFeedList({ signals, loading, onMarkRead }: SignalFeedListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Signal Feed</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="animate-pulse space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-muted rounded" />
            ))}
          </div>
        ) : signals.length === 0 ? (
          <p className="text-muted-foreground text-sm text-center py-8">
            No signals found. Configure your subscription to receive market intelligence.
          </p>
        ) : (
          <div className="space-y-3">
            {signals.map((signal) => (
              <div
                key={signal.id}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  signal.is_read ? "opacity-60" : "hover:bg-muted/50"
                }`}
                onClick={() => !signal.is_read && onMarkRead(signal.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded ${
                          SIGNAL_TYPE_COLORS[signal.signal_type]
                        }`}
                      >
                        {SIGNAL_TYPE_LABELS[signal.signal_type]}
                      </span>
                      {!signal.is_read && (
                        <span className="w-2 h-2 rounded-full bg-primary" />
                      )}
                    </div>
                    <p className="font-medium text-sm">{signal.title}</p>
                    {signal.agency && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {signal.agency}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                    <Badge variant="outline">
                      {Math.round(signal.relevance_score)}%
                    </Badge>
                    {signal.source_url && (
                      <a
                        href={signal.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-primary hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        Source
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
