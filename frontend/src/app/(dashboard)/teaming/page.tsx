"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { teamingBoardApi } from "@/lib/api";
import type {
  CapabilityGapResult,
  TeamingDigestPreview,
  TeamingDigestSchedule,
  TeamingPartnerCohortDrilldownResponse,
  TeamingPartnerPublicProfile,
  TeamingPartnerTrendDrilldownResponse,
  TeamingRequest,
  TeamingRequestTrend,
} from "@/types";
import { NDATracker } from "@/components/teaming/nda-tracker";
import { PerformanceRatingForm } from "@/components/teaming/performance-rating-form";
import { PartnerSearchFilters } from "./_components/partner-search-filters";
import { PartnerFitAnalysis } from "./_components/partner-fit-analysis";
import { PartnerResultsList } from "./_components/partner-results-list";
import { RequestInsightsPanel } from "./_components/request-insights-panel";
import { SentRequestsList } from "./_components/sent-requests-list";
import { ReceivedRequestsList } from "./_components/received-requests-list";
import { SendRequestModal } from "./_components/send-request-modal";

type Tab = "search" | "sent" | "received" | "ndas" | "ratings";

export default function TeamingBoardPage() {
  const [activeTab, setActiveTab] = useState<Tab>("search");
  const [partners, setPartners] = useState<TeamingPartnerPublicProfile[]>([]);
  const [sentRequests, setSentRequests] = useState<TeamingRequest[]>([]);
  const [receivedRequests, setReceivedRequests] = useState<TeamingRequest[]>([]);
  const [requestFitTrends, setRequestFitTrends] = useState<TeamingRequestTrend | null>(null);
  const [partnerDrilldowns, setPartnerDrilldowns] =
    useState<TeamingPartnerTrendDrilldownResponse | null>(null);
  const [partnerCohorts, setPartnerCohorts] =
    useState<TeamingPartnerCohortDrilldownResponse | null>(null);
  const [digestSchedule, setDigestSchedule] = useState<TeamingDigestSchedule | null>(null);
  const [digestPreview, setDigestPreview] = useState<TeamingDigestPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search filters
  const [query, setQuery] = useState("");
  const [naicsFilter, setNaicsFilter] = useState("");
  const [capabilityFilter, setCapabilityFilter] = useState("");
  const [clearanceFilter, setClearanceFilter] = useState("");
  const [gapRfpId, setGapRfpId] = useState("");
  const [gapLoading, setGapLoading] = useState(false);
  const [gapResult, setGapResult] = useState<CapabilityGapResult | null>(null);

  // Request modal state
  const [requestPartnerId, setRequestPartnerId] = useState<number | null>(null);
  const [requestMessage, setRequestMessage] = useState("");

  const fetchPartners = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (query) params.q = query;
      if (naicsFilter) params.naics = naicsFilter;
      if (capabilityFilter) params.capability = capabilityFilter;
      if (clearanceFilter) params.clearance = clearanceFilter;
      const data = await teamingBoardApi.searchPartners(params);
      setPartners(data);
    } catch {
      setError("Failed to search partners.");
    } finally {
      setLoading(false);
    }
  }, [query, naicsFilter, capabilityFilter, clearanceFilter]);

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sent, received, fitTrends, partnerTrends, partnerCohortData, schedule] = await Promise.all([
        teamingBoardApi.listRequests("sent"),
        teamingBoardApi.listRequests("received"),
        teamingBoardApi.getRequestFitTrends(30).catch(
          () => null as TeamingRequestTrend | null
        ),
        teamingBoardApi.getPartnerTrends(30).catch(
          () => null as TeamingPartnerTrendDrilldownResponse | null
        ),
        teamingBoardApi.getPartnerCohorts(30).catch(
          () => null as TeamingPartnerCohortDrilldownResponse | null
        ),
        teamingBoardApi.getDigestSchedule().catch(
          () => null as TeamingDigestSchedule | null
        ),
      ]);
      setSentRequests(sent);
      setReceivedRequests(received);
      setRequestFitTrends(fitTrends);
      setPartnerDrilldowns(partnerTrends);
      setPartnerCohorts(partnerCohortData);
      setDigestSchedule(schedule);
    } catch {
      setError("Failed to load teaming requests.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "search") {
      fetchPartners();
    } else {
      fetchRequests();
    }
  }, [activeTab, fetchPartners, fetchRequests]);

  const handleSendRequest = async () => {
    if (!requestPartnerId) return;
    try {
      await teamingBoardApi.sendRequest({
        to_partner_id: requestPartnerId,
        message: requestMessage || undefined,
      });
      setRequestPartnerId(null);
      setRequestMessage("");
      fetchPartners();
    } catch {
      setError("Failed to send teaming request.");
    }
  };

  const handleUpdateRequest = async (requestId: number, status: "accepted" | "declined") => {
    try {
      await teamingBoardApi.updateRequest(requestId, status);
      fetchRequests();
    } catch {
      setError(`Failed to ${status} request.`);
    }
  };

  const handleGapAnalysis = async () => {
    const rfpId = Number.parseInt(gapRfpId, 10);
    if (!Number.isFinite(rfpId) || rfpId <= 0) {
      setError("Enter a valid RFP ID to run partner-fit analysis.");
      return;
    }
    setGapLoading(true);
    setError(null);
    try {
      const result = await teamingBoardApi.getGapAnalysis(rfpId);
      setGapResult(result);
    } catch {
      setError("Failed to run partner-fit analysis.");
    } finally {
      setGapLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Teaming Board"
        description="Discover partners and manage teaming requests"
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

        {/* Tab Navigation */}
        <div className="flex gap-2 border-b pb-2">
          {(["search", "sent", "received", "ndas", "ratings"] as Tab[]).map((tab) => (
            <Button
              key={tab}
              variant={activeTab === tab ? "default" : "ghost"}
              size="sm"
              onClick={() => setActiveTab(tab)}
            >
              {tab === "search" && "Partner Search"}
              {tab === "sent" && `Sent (${sentRequests.length})`}
              {tab === "received" && `Inbox (${receivedRequests.length})`}
              {tab === "ndas" && "NDA Tracking"}
              {tab === "ratings" && "Ratings"}
            </Button>
          ))}
        </div>

        {/* Search Tab */}
        {activeTab === "search" && (
          <>
            <PartnerSearchFilters
              query={query}
              naicsFilter={naicsFilter}
              capabilityFilter={capabilityFilter}
              clearanceFilter={clearanceFilter}
              onQueryChange={setQuery}
              onNaicsChange={setNaicsFilter}
              onCapabilityChange={setCapabilityFilter}
              onClearanceChange={setClearanceFilter}
              onSearch={fetchPartners}
            />
            <PartnerFitAnalysis
              gapRfpId={gapRfpId}
              gapLoading={gapLoading}
              gapResult={gapResult}
              onRfpIdChange={setGapRfpId}
              onAnalyze={handleGapAnalysis}
            />
            <PartnerResultsList
              partners={partners}
              loading={loading}
              gapResult={gapResult}
              onRequestTeaming={setRequestPartnerId}
            />
          </>
        )}

        {/* Sent Requests Tab */}
        {activeTab === "sent" && (
          <div className="space-y-4">
            <RequestInsightsPanel
              direction="sent"
              requestFitTrends={requestFitTrends}
              partnerDrilldowns={partnerDrilldowns}
              partnerCohorts={partnerCohorts}
              digestSchedule={digestSchedule}
              digestPreview={digestPreview}
              onDigestScheduleChange={setDigestSchedule}
              onDigestPreviewChange={setDigestPreview}
              onError={setError}
            />
            <SentRequestsList requests={sentRequests} loading={loading} />
          </div>
        )}

        {/* Received Requests Tab */}
        {activeTab === "received" && (
          <div className="space-y-4">
            <RequestInsightsPanel
              direction="received"
              requestFitTrends={requestFitTrends}
              partnerDrilldowns={partnerDrilldowns}
              partnerCohorts={partnerCohorts}
              digestSchedule={digestSchedule}
              digestPreview={digestPreview}
              onDigestScheduleChange={setDigestSchedule}
              onDigestPreviewChange={setDigestPreview}
              onError={setError}
            />
            <ReceivedRequestsList
              requests={receivedRequests}
              loading={loading}
              onUpdateRequest={handleUpdateRequest}
            />
          </div>
        )}

        {/* NDA Tracking Tab */}
        {activeTab === "ndas" && <NDATracker />}

        {/* Ratings Tab */}
        {activeTab === "ratings" && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Partner Performance Ratings</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Select a partner from the search tab to rate, or rate a partner below by ID.
                </p>
                <PerformanceRatingForm partnerId={0} />
              </CardContent>
            </Card>
          </div>
        )}

        {/* Send Request Modal */}
        {requestPartnerId !== null && (
          <SendRequestModal
            requestMessage={requestMessage}
            onMessageChange={setRequestMessage}
            onSend={handleSendRequest}
            onCancel={() => {
              setRequestPartnerId(null);
              setRequestMessage("");
            }}
          />
        )}
      </div>
    </div>
  );
}
