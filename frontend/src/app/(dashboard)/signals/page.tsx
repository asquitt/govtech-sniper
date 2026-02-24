"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
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
import { SubscriptionSettings } from "./_components/subscription-settings";
import { AutomationCard } from "./_components/automation-card";
import { DigestPreviewCard } from "./_components/digest-preview-card";
import { SignalFeedList } from "./_components/signal-feed-list";

const SIGNAL_TYPE_LABELS: Record<SignalType, string> = {
  budget: "Budget",
  award: "Award",
  news: "News",
  congressional: "Congressional",
  recompete: "Recompete",
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
          <SubscriptionSettings
            keywords={keywords}
            digestEnabled={digestEnabled}
            digestFrequency={digestFrequency}
            onKeywordsChange={setKeywords}
            onDigestEnabledChange={setDigestEnabled}
            onDigestFrequencyChange={setDigestFrequency}
            onSave={handleSaveSubscription}
          />
        )}

        <AutomationCard
          isIngestingNews={isIngestingNews}
          isAnalyzingBudget={isAnalyzingBudget}
          isRescoring={isRescoring}
          isPreviewingDigest={isPreviewingDigest}
          isSendingDigest={isSendingDigest}
          onIngestNews={handleIngestNews}
          onAnalyzeBudget={handleAnalyzeBudget}
          onRescore={handleRescore}
          onPreviewDigest={handlePreviewDigest}
          onSendDigest={handleSendDigest}
        />

        {digestPreview && (
          <DigestPreviewCard
            digestPreview={digestPreview}
            lastDigestSend={lastDigestSend}
          />
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

        <SignalFeedList
          signals={signals}
          loading={loading}
          onMarkRead={handleMarkRead}
        />
      </div>
    </div>
  );
}
