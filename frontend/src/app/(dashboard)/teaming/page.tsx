"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { teamingBoardApi } from "@/lib/api";
import type { TeamingPartnerPublicProfile, TeamingRequest } from "@/types";
import { NDATracker } from "@/components/teaming/nda-tracker";
import { PerformanceRatingForm } from "@/components/teaming/performance-rating-form";

type Tab = "search" | "sent" | "received" | "ndas" | "ratings";

export default function TeamingBoardPage() {
  const [activeTab, setActiveTab] = useState<Tab>("search");
  const [partners, setPartners] = useState<TeamingPartnerPublicProfile[]>([]);
  const [sentRequests, setSentRequests] = useState<TeamingRequest[]>([]);
  const [receivedRequests, setReceivedRequests] = useState<TeamingRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search filters
  const [query, setQuery] = useState("");
  const [naicsFilter, setNaicsFilter] = useState("");
  const [capabilityFilter, setCapabilityFilter] = useState("");
  const [clearanceFilter, setClearanceFilter] = useState("");

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
      const [sent, received] = await Promise.all([
        teamingBoardApi.listRequests("sent"),
        teamingBoardApi.listRequests("received"),
      ]);
      setSentRequests(sent);
      setReceivedRequests(received);
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

  const statusBadgeVariant = (status: string) => {
    if (status === "accepted") return "default" as const;
    if (status === "declined") return "destructive" as const;
    return "secondary" as const;
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
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setRequestPartnerId(p.id)}
                          >
                            Request Teaming
                          </Button>
                        </div>
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
                      </div>
                      <Badge variant={statusBadgeVariant(r.status)}>{r.status}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Received Requests Tab */}
        {activeTab === "received" && (
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
                        <p className="font-medium">From User #{r.from_user_id}</p>
                        {r.message && (
                          <p className="text-xs text-muted-foreground mt-1">{r.message}</p>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">
                          Received: {new Date(r.created_at).toLocaleDateString()}
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
