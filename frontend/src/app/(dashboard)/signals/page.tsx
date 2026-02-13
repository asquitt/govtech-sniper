"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SignalType } from "@/types/signals";
import {
  useSignalFeed,
  useSignalSubscription,
  useMarkSignalRead,
  useUpsertSubscription,
} from "@/hooks/use-signals";

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

export default function SignalsPage() {
  const [filter, setFilter] = useState<SignalType | undefined>(undefined);
  const [showSettings, setShowSettings] = useState(false);
  const [keywords, setKeywords] = useState("");
  const [error, setError] = useState<string | null>(null);

  const feedParams = useMemo(
    () => ({ signal_type: filter, limit: 50 }),
    [filter]
  );
  const { data: feedData, isLoading: loading } = useSignalFeed(feedParams);
  const { data: subscription } = useSignalSubscription();
  const markRead = useMarkSignalRead();
  const upsertSub = useUpsertSubscription();

  const signals = feedData?.signals ?? [];
  const total = feedData?.total ?? 0;

  // Sync keywords from subscription on first load
  useEffect(() => {
    if (subscription?.keywords) {
      setKeywords(subscription.keywords.join(", "));
    }
  }, [subscription]);

  const handleMarkRead = (id: number) => {
    markRead.mutate(id, {
      onError: () => setError("Failed to mark signal as read."),
    });
  };

  const handleSaveSubscription = () => {
    upsertSub.mutate(
      {
        agencies: subscription?.agencies ?? [],
        naics_codes: subscription?.naics_codes ?? [],
        keywords: keywords
          .split(",")
          .map((k) => k.trim())
          .filter(Boolean),
        email_digest_enabled: subscription?.email_digest_enabled ?? false,
        digest_frequency: subscription?.digest_frequency ?? "daily",
      },
      {
        onSuccess: () => setShowSettings(false),
        onError: () => setError("Failed to save subscription."),
      }
    );
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Market Signals"
        description="Daily intelligence feed for budget, award, and recompete signals"
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSettings(!showSettings)}
          >
            {showSettings ? "Close Settings" : "Subscription Settings"}
          </Button>
        }
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {error && (
          <div className="bg-destructive/10 text-destructive rounded-lg p-4 flex items-center justify-between">
            <span>{error}</span>
            <Button variant="ghost" size="sm" onClick={() => setError(null)}>
              Dismiss
            </Button>
          </div>
        )}

        {/* Subscription Settings */}
        {showSettings && (
          <Card>
            <CardHeader>
              <CardTitle>Subscription Preferences</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <label className="text-sm font-medium">Keywords (comma-separated)</label>
                <input
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-background mt-1"
                  placeholder="cybersecurity, cloud, AI/ML"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                />
              </div>
              <Button size="sm" onClick={handleSaveSubscription}>
                Save Preferences
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Filter bar */}
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={!filter ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(undefined)}
          >
            All ({total})
          </Button>
          {(Object.keys(SIGNAL_TYPE_LABELS) as SignalType[]).map((type) => (
            <Button
              key={type}
              variant={filter === type ? "default" : "outline"}
              size="sm"
              onClick={() => setFilter(type)}
            >
              {SIGNAL_TYPE_LABELS[type]}
            </Button>
          ))}
        </div>

        {/* Signal Feed */}
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
                    onClick={() => !signal.is_read && handleMarkRead(signal.id)}
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
      </div>
    </div>
  );
}
