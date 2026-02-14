"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type {
  SignalDigestPreview,
  SignalDigestSendResponse,
  SignalType,
} from "@/types/signals";
import { signalApi } from "@/lib/api/signals";
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
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<SignalType | undefined>(undefined);
  const [showSettings, setShowSettings] = useState(false);
  const [keywords, setKeywords] = useState("");
  const [digestEnabled, setDigestEnabled] = useState(false);
  const [digestFrequency, setDigestFrequency] = useState<"daily" | "weekly">("daily");
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [digestPreview, setDigestPreview] = useState<SignalDigestPreview | null>(null);
  const [lastDigestSend, setLastDigestSend] = useState<SignalDigestSendResponse | null>(null);
  const [isIngestingNews, setIsIngestingNews] = useState(false);
  const [isAnalyzingBudget, setIsAnalyzingBudget] = useState(false);
  const [isRescoring, setIsRescoring] = useState(false);
  const [isPreviewingDigest, setIsPreviewingDigest] = useState(false);
  const [isSendingDigest, setIsSendingDigest] = useState(false);

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

  useEffect(() => {
    if (!subscription) return;
    setKeywords(subscription.keywords.join(", "));
    setDigestEnabled(subscription.email_digest_enabled);
    setDigestFrequency(subscription.digest_frequency);
  }, [subscription]);

  const refreshSignalData = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["signal-feed"] }),
      queryClient.invalidateQueries({ queryKey: ["signal-subscription"] }),
    ]);
  };

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
        email_digest_enabled: digestEnabled,
        digest_frequency: digestFrequency,
      },
      {
        onSuccess: () => {
          setShowSettings(false);
          setActionMessage("Subscription preferences saved.");
        },
        onError: () => setError("Failed to save subscription."),
      }
    );
  };

  const handleIngestNews = async () => {
    setIsIngestingNews(true);
    setError(null);
    setActionMessage(null);
    try {
      const result = await signalApi.ingestNews({ max_items_per_source: 8 });
      setActionMessage(
        `News ingestion completed: ${result.created} created, ${result.skipped} skipped duplicates.`
      );
      await refreshSignalData();
    } catch {
      setError("Failed to ingest news sources.");
    } finally {
      setIsIngestingNews(false);
    }
  };

  const handleAnalyzeBudget = async () => {
    setIsAnalyzingBudget(true);
    setError(null);
    setActionMessage(null);
    try {
      const result = await signalApi.ingestBudgetAnalysis({ limit: 25 });
      setActionMessage(`Budget analysis completed: ${result.created} budget signals generated.`);
      await refreshSignalData();
    } catch {
      setError("Failed to analyze budget documents.");
    } finally {
      setIsAnalyzingBudget(false);
    }
  };

  const handleRescore = async () => {
    setIsRescoring(true);
    setError(null);
    setActionMessage(null);
    try {
      const result = await signalApi.rescore({ unread_only: false });
      setActionMessage(
        `Signals rescored: ${result.updated} updated (avg relevance ${result.average_score}%).`
      );
      await refreshSignalData();
    } catch {
      setError("Failed to rescore signals.");
    } finally {
      setIsRescoring(false);
    }
  };

  const handlePreviewDigest = async () => {
    setIsPreviewingDigest(true);
    setError(null);
    try {
      const preview = await signalApi.digestPreview({
        period_days: digestFrequency === "weekly" ? 7 : 1,
      });
      setDigestPreview(preview);
      setLastDigestSend(null);
    } catch {
      setError("Failed to load digest preview.");
    } finally {
      setIsPreviewingDigest(false);
    }
  };

  const handleSendDigest = async () => {
    setIsSendingDigest(true);
    setError(null);
    try {
      const sent = await signalApi.sendDigest({
        period_days: digestFrequency === "weekly" ? 7 : 1,
      });
      setLastDigestSend(sent);
      setDigestPreview(sent);
      setActionMessage(
        `Digest sent to ${sent.recipient_email} with ${sent.included_count} signal highlights.`
      );
    } catch {
      setError("Failed to send digest. Ensure digest is enabled in subscription settings.");
    } finally {
      setIsSendingDigest(false);
    }
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

        {actionMessage && (
          <div
            data-testid="signals-action-message"
            className="rounded-lg border border-green-300 bg-green-50 px-4 py-3 text-sm text-green-800"
          >
            {actionMessage}
          </div>
        )}

        {showSettings && (
          <Card>
            <CardHeader>
              <CardTitle>Subscription Preferences</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">Keywords (comma-separated)</label>
                <input
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-background mt-1"
                  placeholder="cybersecurity, cloud, AI/ML"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                />
              </div>

              <div className="flex items-center gap-3">
                <input
                  id="signals-digest-enabled"
                  type="checkbox"
                  checked={digestEnabled}
                  onChange={(event) => setDigestEnabled(event.target.checked)}
                />
                <label htmlFor="signals-digest-enabled" className="text-sm">
                  Enable market signals email digest
                </label>
              </div>

              <div>
                <label className="text-sm font-medium">Digest Frequency</label>
                <select
                  className="mt-1 w-full border rounded-lg px-3 py-2 text-sm bg-background"
                  value={digestFrequency}
                  onChange={(event) =>
                    setDigestFrequency(event.target.value as "daily" | "weekly")
                  }
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                </select>
              </div>

              <Button size="sm" onClick={handleSaveSubscription}>
                Save Preferences
              </Button>
            </CardContent>
          </Card>
        )}

        <Card data-testid="signals-automation-card">
          <CardHeader>
            <CardTitle>Automation</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={handleIngestNews} disabled={isIngestingNews}>
              {isIngestingNews ? "Ingesting..." : "Ingest News"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleAnalyzeBudget}
              disabled={isAnalyzingBudget}
            >
              {isAnalyzingBudget ? "Analyzing..." : "Analyze Budget Docs"}
            </Button>
            <Button size="sm" variant="outline" onClick={handleRescore} disabled={isRescoring}>
              {isRescoring ? "Rescoring..." : "Rescore Signals"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handlePreviewDigest}
              disabled={isPreviewingDigest}
            >
              {isPreviewingDigest ? "Loading..." : "Preview Digest"}
            </Button>
            <Button size="sm" onClick={handleSendDigest} disabled={isSendingDigest}>
              {isSendingDigest ? "Sending..." : "Send Digest"}
            </Button>
          </CardContent>
        </Card>

        {digestPreview && (
          <Card data-testid="signals-digest-preview-card">
            <CardHeader>
              <CardTitle>Digest Preview ({digestPreview.period_days} day window)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                {digestPreview.included_count} of {digestPreview.total_unread} unread signals included.
              </p>
              <div className="flex gap-2 flex-wrap">
                {Object.entries(digestPreview.type_breakdown).map(([type, count]) => (
                  <Badge key={type} variant="outline">
                    {type}: {count}
                  </Badge>
                ))}
              </div>
              {lastDigestSend && (
                <p className="text-xs text-muted-foreground">
                  Last sent to {lastDigestSend.recipient_email} at{" "}
                  {new Date(lastDigestSend.sent_at).toLocaleString()}.
                </p>
              )}
              <div className="space-y-2">
                {digestPreview.top_signals.map((item) => (
                  <div key={item.signal_id} className="rounded border p-2">
                    <p className="text-sm font-medium">{item.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {Math.round(item.relevance_score)}% relevance
                      {item.agency ? ` • ${item.agency}` : ""}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

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
