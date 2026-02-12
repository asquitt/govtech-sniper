"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { teamingBoardApi } from "@/lib/api";
import type {
  CapabilityGapResult,
  TeamingDigestPreview,
  TeamingDigestSchedule,
  TeamingPartnerPublicProfile,
  TeamingPartnerTrendDrilldownResponse,
  TeamingRequest,
  TeamingRequestTrend,
} from "@/types";
import { NDATracker } from "@/components/teaming/nda-tracker";
import { PerformanceRatingForm } from "@/components/teaming/performance-rating-form";

type Tab = "search" | "sent" | "received" | "ndas" | "ratings";

export default function TeamingBoardPage() {
  const [activeTab, setActiveTab] = useState<Tab>("search");
  const [partners, setPartners] = useState<TeamingPartnerPublicProfile[]>([]);
  const [sentRequests, setSentRequests] = useState<TeamingRequest[]>([]);
  const [receivedRequests, setReceivedRequests] = useState<TeamingRequest[]>([]);
  const [requestFitTrends, setRequestFitTrends] = useState<TeamingRequestTrend | null>(null);
  const [partnerDrilldowns, setPartnerDrilldowns] =
    useState<TeamingPartnerTrendDrilldownResponse | null>(null);
  const [digestSchedule, setDigestSchedule] = useState<TeamingDigestSchedule | null>(null);
  const [digestPreview, setDigestPreview] = useState<TeamingDigestPreview | null>(null);
  const [isExportingTimeline, setIsExportingTimeline] = useState(false);
  const [isSavingDigestSchedule, setIsSavingDigestSchedule] = useState(false);
  const [isSendingDigest, setIsSendingDigest] = useState(false);
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
      const [sent, received, fitTrends, partnerTrends, schedule] = await Promise.all([
        teamingBoardApi.listRequests("sent"),
        teamingBoardApi.listRequests("received"),
        teamingBoardApi.getRequestFitTrends(30).catch(
          () => null as TeamingRequestTrend | null
        ),
        teamingBoardApi.getPartnerTrends(30).catch(
          () => null as TeamingPartnerTrendDrilldownResponse | null
        ),
        teamingBoardApi.getDigestSchedule().catch(
          () => null as TeamingDigestSchedule | null
        ),
      ]);
      setSentRequests(sent);
      setReceivedRequests(received);
      setRequestFitTrends(fitTrends);
      setPartnerDrilldowns(partnerTrends);
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

  const statusBadgeVariant = (status: string) => {
    if (status === "accepted") return "default" as const;
    if (status === "declined") return "destructive" as const;
    return "secondary" as const;
  };

  const recentTrendPoints = (requestFitTrends?.points ?? []).slice(-7).reverse();

  const renderRequestInsights = (direction: "sent" | "received" | "all") => (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>Teaming Fit Trends</CardTitle>
        <Button
          size="sm"
          variant="outline"
          data-testid="teaming-export-audit"
          disabled={isExportingTimeline}
          onClick={async () => {
            setIsExportingTimeline(true);
            try {
              const blob = await teamingBoardApi.exportRequestAuditCsv(direction, 30);
              const url = window.URL.createObjectURL(blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = "teaming_requests_audit.csv";
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
              window.URL.revokeObjectURL(url);
            } catch {
              setError("Failed to export request audit timeline.");
            } finally {
              setIsExportingTimeline(false);
            }
          }}
        >
          Export Timeline CSV
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground lg:grid-cols-4">
          <div className="rounded border border-border px-2 py-1">
            Total sent:{" "}
            <span data-testid="teaming-total-sent" className="font-semibold text-foreground">
              {requestFitTrends?.total_sent ?? 0}
            </span>
          </div>
          <div className="rounded border border-border px-2 py-1">
            Accepted:{" "}
            <span data-testid="teaming-accepted-count" className="font-semibold text-foreground">
              {requestFitTrends?.accepted_count ?? 0}
            </span>
          </div>
          <div className="rounded border border-border px-2 py-1">
            Pending:{" "}
            <span data-testid="teaming-pending-count" className="font-semibold text-foreground">
              {requestFitTrends?.pending_count ?? 0}
            </span>
          </div>
          <div className="rounded border border-border px-2 py-1">
            Acceptance rate:{" "}
            <span data-testid="teaming-acceptance-rate" className="font-semibold text-foreground">
              {requestFitTrends ? `${requestFitTrends.acceptance_rate}%` : "0%"}
            </span>
          </div>
        </div>
        {recentTrendPoints.length > 0 && (
          <div className="rounded border border-border p-2 text-[11px] text-muted-foreground">
            <p className="mb-1 font-medium text-foreground">Last 7 days fit-score trend</p>
            <div className="space-y-1">
              {recentTrendPoints.map((point) => (
                <div
                  key={point.date}
                  className="flex items-center justify-between rounded border border-border/60 px-2 py-1"
                >
                  <span>{point.date}</span>
                  <span>
                    sent {point.sent_count} / accepted {point.accepted_count} / fit{" "}
                    {point.fit_score}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="rounded border border-border p-2 text-[11px] text-muted-foreground">
          <p className="mb-1 font-medium text-foreground">Partner Drilldowns</p>
          {partnerDrilldowns && partnerDrilldowns.partners.length > 0 ? (
            <div className="space-y-1">
              {partnerDrilldowns.partners.slice(0, 5).map((partner) => (
                <div
                  key={partner.partner_id}
                  className="flex items-center justify-between rounded border border-border/60 px-2 py-1"
                  data-testid={`partner-drilldown-${partner.partner_id}`}
                >
                  <span>{partner.partner_name}</span>
                  <span>
                    sent {partner.sent_count} / accepted {partner.accepted_count} / rate{" "}
                    {partner.acceptance_rate}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p>No partner drilldown data yet.</p>
          )}
        </div>
        <div className="rounded border border-border p-2 text-[11px] text-muted-foreground space-y-2">
          <div className="flex items-center justify-between gap-2">
            <p className="font-medium text-foreground">Teaming Performance Digest</p>
            <Button
              size="sm"
              variant="outline"
              disabled={isSendingDigest || !digestSchedule?.is_enabled}
              onClick={async () => {
                setIsSendingDigest(true);
                try {
                  const preview = await teamingBoardApi.sendDigest(30);
                  setDigestPreview(preview);
                  setDigestSchedule(preview.schedule);
                } catch {
                  setError("Failed to send teaming digest.");
                } finally {
                  setIsSendingDigest(false);
                }
              }}
            >
              Send Digest
            </Button>
          </div>
          {digestSchedule ? (
            <>
              <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
                <label className="space-y-1">
                  Frequency
                  <select
                    className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                    aria-label="Teaming digest frequency"
                    value={digestSchedule.frequency}
                    onChange={(event) =>
                      setDigestSchedule((prev) =>
                        prev
                          ? {
                              ...prev,
                              frequency: event.target.value as "daily" | "weekly",
                            }
                          : prev
                      )
                    }
                  >
                    <option value="daily">daily</option>
                    <option value="weekly">weekly</option>
                  </select>
                </label>
                <label className="space-y-1">
                  Day
                  <input
                    aria-label="Teaming digest day"
                    type="number"
                    min={0}
                    max={6}
                    className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                    value={digestSchedule.day_of_week ?? 1}
                    onChange={(event) =>
                      setDigestSchedule((prev) =>
                        prev
                          ? {
                              ...prev,
                              day_of_week: Number.parseInt(event.target.value, 10) || 0,
                            }
                          : prev
                      )
                    }
                  />
                </label>
                <label className="space-y-1">
                  Hour UTC
                  <input
                    aria-label="Teaming digest hour"
                    type="number"
                    min={0}
                    max={23}
                    className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                    value={digestSchedule.hour_utc}
                    onChange={(event) =>
                      setDigestSchedule((prev) =>
                        prev
                          ? { ...prev, hour_utc: Number.parseInt(event.target.value, 10) || 0 }
                          : prev
                      )
                    }
                  />
                </label>
                <label className="space-y-1">
                  Minute UTC
                  <input
                    aria-label="Teaming digest minute"
                    type="number"
                    min={0}
                    max={59}
                    className="h-8 w-full rounded border border-input bg-background px-2 text-xs"
                    value={digestSchedule.minute_utc}
                    onChange={(event) =>
                      setDigestSchedule((prev) =>
                        prev
                          ? {
                              ...prev,
                              minute_utc: Number.parseInt(event.target.value, 10) || 0,
                            }
                          : prev
                      )
                    }
                  />
                </label>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    aria-label="Teaming digest include declined"
                    checked={digestSchedule.include_declined_reasons}
                    onChange={(event) =>
                      setDigestSchedule((prev) =>
                        prev
                          ? { ...prev, include_declined_reasons: event.target.checked }
                          : prev
                      )
                    }
                  />
                  include declined metrics
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    aria-label="Teaming digest enabled"
                    checked={digestSchedule.is_enabled}
                    onChange={(event) =>
                      setDigestSchedule((prev) =>
                        prev ? { ...prev, is_enabled: event.target.checked } : prev
                      )
                    }
                  />
                  enabled
                </label>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={isSavingDigestSchedule}
                  onClick={async () => {
                    if (!digestSchedule) return;
                    setIsSavingDigestSchedule(true);
                    try {
                      const updated = await teamingBoardApi.updateDigestSchedule({
                        frequency: digestSchedule.frequency,
                        day_of_week: digestSchedule.day_of_week,
                        hour_utc: digestSchedule.hour_utc,
                        minute_utc: digestSchedule.minute_utc,
                        channel: digestSchedule.channel,
                        include_declined_reasons:
                          digestSchedule.include_declined_reasons,
                        is_enabled: digestSchedule.is_enabled,
                      });
                      setDigestSchedule(updated);
                    } catch {
                      setError("Failed to save digest schedule.");
                    } finally {
                      setIsSavingDigestSchedule(false);
                    }
                  }}
                >
                  Save Schedule
                </Button>
              </div>
              <p>
                Last sent:{" "}
                {digestSchedule.last_sent_at
                  ? new Date(digestSchedule.last_sent_at).toLocaleString()
                  : "never"}
              </p>
              {digestPreview ? (
                <p data-testid="teaming-digest-preview">
                  Preview top partners: {digestPreview.top_partners.length}
                </p>
              ) : null}
            </>
          ) : (
            <p>Digest schedule unavailable.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );

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
            {/* Filters */}
            <Card>
              <CardContent className="pt-4">
                <div className="grid grid-cols-4 gap-3">
                  <input
                    className="border rounded-lg px-3 py-2 text-sm bg-background"
                    placeholder="Company name..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                  <input
                    className="border rounded-lg px-3 py-2 text-sm bg-background"
                    placeholder="NAICS code"
                    value={naicsFilter}
                    onChange={(e) => setNaicsFilter(e.target.value)}
                  />
                  <input
                    className="border rounded-lg px-3 py-2 text-sm bg-background"
                    placeholder="Capability"
                    value={capabilityFilter}
                    onChange={(e) => setCapabilityFilter(e.target.value)}
                  />
                  <input
                    className="border rounded-lg px-3 py-2 text-sm bg-background"
                    placeholder="Clearance level"
                    value={clearanceFilter}
                    onChange={(e) => setClearanceFilter(e.target.value)}
                  />
                </div>
                <div className="mt-3">
                  <Button size="sm" onClick={fetchPartners}>
                    Search
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Partner Fit Analysis</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap items-end gap-2">
                  <div>
                    <label className="mb-1 block text-xs text-muted-foreground">
                      RFP ID
                    </label>
                    <input
                      className="border rounded-lg px-3 py-2 text-sm bg-background"
                      placeholder="123"
                      type="number"
                      min={1}
                      aria-label="RFP ID"
                      value={gapRfpId}
                      onChange={(event) => setGapRfpId(event.target.value)}
                    />
                  </div>
                  <Button
                    size="sm"
                    onClick={handleGapAnalysis}
                    disabled={gapLoading || !gapRfpId.trim()}
                  >
                    Analyze Fit
                  </Button>
                </div>
                {gapResult && (
                  <div className="rounded-lg border border-border p-3 text-sm">
                    <p className="font-medium text-foreground">{gapResult.analysis_summary}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Gaps: {gapResult.gaps.length} &middot; Recommended partners:{" "}
                      {gapResult.recommended_partners.length}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Results */}
            <Card>
              <CardHeader>
                <CardTitle>Public Partners ({partners.length})</CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="animate-pulse space-y-3">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-20 bg-muted rounded" />
                    ))}
                  </div>
                ) : partners.length === 0 ? (
                  <p className="text-muted-foreground text-sm text-center py-8">
                    No public partners found. Try adjusting your filters.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {partners.map((p) => (
                      <div key={p.id} className="border rounded-lg p-4">
                        {(() => {
                          const gapMatches = gapResult
                            ? gapResult.gaps.filter((gap) =>
                                gap.matching_partner_ids.includes(p.id)
                              )
                            : [];
                          const recommendedReason = gapResult?.recommended_partners.find(
                            (partner) => partner.partner_id === p.id
                          )?.reason;
                          const hasFitSignal =
                            gapMatches.length > 0 || Boolean(recommendedReason);
                          return (
                            <>
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <p className="font-medium">{p.name}</p>
                              {p.partner_type && (
                                <Badge variant="outline">{p.partner_type}</Badge>
                              )}
                            </div>
                            <div className="flex flex-wrap gap-1 mt-2">
                              {p.naics_codes.map((code) => (
                                <Badge key={code} variant="secondary" className="text-xs">
                                  NAICS: {code}
                                </Badge>
                              ))}
                              {p.set_asides.map((sa) => (
                                <Badge key={sa} variant="secondary" className="text-xs">
                                  {sa}
                                </Badge>
                              ))}
                              {p.clearance_level && (
                                <Badge variant="secondary" className="text-xs">
                                  {p.clearance_level}
                                </Badge>
                              )}
                            </div>
                            {p.capabilities.length > 0 && (
                              <p className="text-xs text-muted-foreground mt-2">
                                Capabilities: {p.capabilities.join(", ")}
                              </p>
                            )}
                            {p.past_performance_summary && (
                              <p className="text-xs text-muted-foreground mt-1">
                                {p.past_performance_summary}
                              </p>
                            )}
                            <div className="flex gap-3 mt-2 text-xs text-muted-foreground">
                              {p.contact_name && <span>Contact: {p.contact_name}</span>}
                              {p.contact_email && <span>{p.contact_email}</span>}
                              {p.website && (
                                <a
                                  href={p.website}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-primary hover:underline"
                                >
                                  Website
                                </a>
                              )}
                            </div>
                            {hasFitSignal && (
                              <div
                                className="mt-2 rounded border border-border bg-secondary/30 p-2 text-xs text-muted-foreground"
                                data-testid={`partner-fit-${p.id}`}
                              >
                                <p className="font-medium text-foreground">Fit rationale</p>
                                {recommendedReason && (
                                  <p className="mt-1">Recommendation: {recommendedReason}</p>
                                )}
                                {gapMatches.length > 0 && (
                                  <p className="mt-1">
                                    Gap matches:{" "}
                                    {gapMatches.map((gap) => gap.description).join("; ")}
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setRequestPartnerId(p.id)}
                          >
                            Request Teaming
                          </Button>
                        </div>
                            </>
                          );
                        })()}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}

        {/* Sent Requests Tab */}
        {activeTab === "sent" && (
          <div className="space-y-4">
            {renderRequestInsights("sent")}
            <Card>
              <CardHeader>
                <CardTitle>Sent Requests</CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="animate-pulse space-y-3">
                    {[1, 2].map((i) => (
                      <div key={i} className="h-16 bg-muted rounded" />
                    ))}
                  </div>
                ) : sentRequests.length === 0 ? (
                  <p className="text-muted-foreground text-sm text-center py-8">
                    No sent requests yet.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {sentRequests.map((r) => (
                      <div key={r.id} className="border rounded-lg p-4 flex items-center justify-between">
                        <div>
                          <p className="font-medium">{r.partner_name || `Partner #${r.to_partner_id}`}</p>
                          {r.message && (
                            <p className="text-xs text-muted-foreground mt-1">{r.message}</p>
                          )}
                          <p className="text-xs text-muted-foreground mt-1">
                            Sent: {new Date(r.created_at).toLocaleDateString()}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            Updated: {new Date(r.updated_at).toLocaleString()}
                          </p>
                        </div>
                        <Badge variant={statusBadgeVariant(r.status)}>{r.status}</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Received Requests Tab */}
        {activeTab === "received" && (
          <div className="space-y-4">
            {renderRequestInsights("received")}
            <Card>
              <CardHeader>
                <CardTitle>Received Requests</CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="animate-pulse space-y-3">
                    {[1, 2].map((i) => (
                      <div key={i} className="h-16 bg-muted rounded" />
                    ))}
                  </div>
                ) : receivedRequests.length === 0 ? (
                  <p className="text-muted-foreground text-sm text-center py-8">
                    No received requests.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {receivedRequests.map((r) => (
                      <div key={r.id} className="border rounded-lg p-4 flex items-center justify-between">
                        <div>
                          <p className="font-medium">
                            {r.from_user_name || r.from_user_email || `From User #${r.from_user_id}`}
                          </p>
                          {r.message && (
                            <p className="text-xs text-muted-foreground mt-1">{r.message}</p>
                          )}
                          <p className="text-xs text-muted-foreground mt-1">
                            Received: {new Date(r.created_at).toLocaleDateString()}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            Updated: {new Date(r.updated_at).toLocaleString()}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant={statusBadgeVariant(r.status)}>{r.status}</Badge>
                          {r.status === "pending" && (
                            <>
                              <Button
                                size="sm"
                                onClick={() => handleUpdateRequest(r.id, "accepted")}
                              >
                                Accept
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleUpdateRequest(r.id, "declined")}
                              >
                                Decline
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
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
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <Card className="w-full max-w-md">
              <CardHeader>
                <CardTitle>Send Teaming Request</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <textarea
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-background min-h-[100px]"
                  placeholder="Include a message (optional)"
                  value={requestMessage}
                  onChange={(e) => setRequestMessage(e.target.value)}
                />
                <div className="flex gap-2 justify-end">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setRequestPartnerId(null);
                      setRequestMessage("");
                    }}
                  >
                    Cancel
                  </Button>
                  <Button size="sm" onClick={handleSendRequest}>
                    Send Request
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
