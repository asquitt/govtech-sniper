"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { captureApi, rfpApi } from "@/lib/api";
import type {
  CapturePlanListItem,
  CaptureStage,
  BidDecision,
  GateReview,
  TeamingPartner,
  TeamingPartnerLink,
  RFPListItem,
} from "@/types";

const stageOptions: { value: CaptureStage; label: string }[] = [
  { value: "identified", label: "Identified" },
  { value: "qualified", label: "Qualified" },
  { value: "pursuit", label: "Pursuit" },
  { value: "proposal", label: "Proposal" },
  { value: "submitted", label: "Submitted" },
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" },
];

const decisionOptions: { value: BidDecision; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "bid", label: "Bid" },
  { value: "no_bid", label: "No Bid" },
];

export default function CapturePage() {
  const [rfps, setRfps] = useState<RFPListItem[]>([]);
  const [plans, setPlans] = useState<CapturePlanListItem[]>([]);
  const [partners, setPartners] = useState<TeamingPartner[]>([]);
  const [partnerLinks, setPartnerLinks] = useState<TeamingPartnerLink[]>([]);
  const [gateReviews, setGateReviews] = useState<GateReview[]>([]);
  const [selectedRfpId, setSelectedRfpId] = useState<number | null>(null);
  const [partnerName, setPartnerName] = useState("");
  const [partnerType, setPartnerType] = useState("");
  const [linkPartnerId, setLinkPartnerId] = useState<number | null>(null);
  const [linkRole, setLinkRole] = useState("");
  const [gateReviewStage, setGateReviewStage] = useState<CaptureStage>("qualified");
  const [gateReviewDecision, setGateReviewDecision] =
    useState<BidDecision>("pending");
  const [gateReviewNotes, setGateReviewNotes] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [rfpList, planList, partnerList] = await Promise.all([
        rfpApi.list({ limit: 100 }),
        captureApi.listPlans(),
        captureApi.listPartners(),
      ]);
      setRfps(rfpList);
      setPlans(planList);
      setPartners(partnerList);
      if (
        rfpList.length > 0 &&
        (selectedRfpId === null ||
          !rfpList.some((rfp) => rfp.id === selectedRfpId))
      ) {
        setSelectedRfpId(rfpList[0].id);
      }
    } catch (err) {
      console.error("Failed to load capture data", err);
      setError("Failed to load capture data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [selectedRfpId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    const fetchRfpDetails = async () => {
      if (!selectedRfpId) return;
      try {
        const [linksResult, reviewsResult] = await Promise.all([
          captureApi.listPartnerLinks(selectedRfpId),
          captureApi.listGateReviews(selectedRfpId),
        ]);
        setPartnerLinks(linksResult.links);
        setGateReviews(reviewsResult);
      } catch (err) {
        console.error("Failed to load capture details", err);
      }
    };
    fetchRfpDetails();
  }, [selectedRfpId]);

  const planByRfp = useMemo(() => {
    const map = new Map<number, CapturePlanListItem>();
    plans.forEach((plan) => map.set(plan.rfp_id, plan));
    return map;
  }, [plans]);

  const handleCreatePlan = async (rfpId: number) => {
    try {
      await captureApi.createPlan({ rfp_id: rfpId });
      await fetchData();
    } catch (err) {
      console.error("Failed to create capture plan", err);
      setError("Failed to create capture plan.");
    }
  };

  const handleUpdatePlan = async (
    planId: number,
    updates: Partial<{ stage: CaptureStage; bid_decision: BidDecision }>
  ) => {
    try {
      await captureApi.updatePlan(planId, updates);
      await fetchData();
    } catch (err) {
      console.error("Failed to update capture plan", err);
      setError("Failed to update capture plan.");
    }
  };

  const handleCreatePartner = async () => {
    if (!partnerName.trim()) return;
    try {
      await captureApi.createPartner({
        name: partnerName.trim(),
        partner_type: partnerType.trim() || undefined,
      });
      setPartnerName("");
      setPartnerType("");
      await fetchData();
    } catch (err) {
      console.error("Failed to create teaming partner", err);
      setError("Failed to create teaming partner.");
    }
  };

  const handleLinkPartner = async () => {
    if (!selectedRfpId || !linkPartnerId) return;
    try {
      await captureApi.linkPartner({
        rfp_id: selectedRfpId,
        partner_id: linkPartnerId,
        role: linkRole.trim() || undefined,
      });
      setLinkRole("");
      const linksResult = await captureApi.listPartnerLinks(selectedRfpId);
      setPartnerLinks(linksResult.links);
    } catch (err) {
      console.error("Failed to link partner", err);
      setError("Failed to link partner.");
    }
  };

  const handleCreateGateReview = async () => {
    if (!selectedRfpId) return;
    try {
      await captureApi.createGateReview({
        rfp_id: selectedRfpId,
        stage: gateReviewStage,
        decision: gateReviewDecision,
        notes: gateReviewNotes.trim() || undefined,
      });
      setGateReviewNotes("");
      const reviews = await captureApi.listGateReviews(selectedRfpId);
      setGateReviews(reviews);
    } catch (err) {
      console.error("Failed to create gate review", err);
      setError("Failed to create gate review.");
    }
  };

  const partnerById = useMemo(() => {
    const map = new Map<number, TeamingPartner>();
    partners.forEach((partner) => map.set(partner.id, partner));
    return map;
  }, [partners]);

  if (error && !isLoading) {
    return (
      <div className="flex flex-col h-full">
        <Header
          title="Capture"
          description="Track bid decisions, gate reviews, and teaming partners"
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={fetchData}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Capture"
        description="Track bid decisions, gate reviews, and teaming partners"
      />

      <div className="flex-1 p-6 overflow-hidden">
        <div className="grid grid-cols-3 gap-4 mb-6">
          <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Total Opportunities</p>
              <p className="text-2xl font-bold text-primary">{rfps.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-accent/5 to-accent/10 border-accent/20">
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Capture Plans</p>
              <p className="text-2xl font-bold text-accent">{plans.length}</p>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-warning/5 to-warning/10 border-warning/20">
            <CardContent className="p-4">
              <p className="text-sm text-muted-foreground">Pending Decisions</p>
              <p className="text-2xl font-bold text-warning">
                {plans.filter((plan) => plan.bid_decision === "pending").length}
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-border text-sm font-medium">
            Capture Pipeline
          </div>
          <div className="divide-y divide-border">
            {rfps.map((rfp) => {
              const plan = planByRfp.get(rfp.id);
              return (
                <div key={rfp.id} className="px-4 py-4 flex flex-col gap-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-base font-semibold text-foreground">
                        {rfp.title}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {rfp.agency || "Unknown agency"}
                      </p>
                    </div>
                    {plan ? (
                      <Badge variant="outline">Plan Active</Badge>
                    ) : (
                      <Badge variant="destructive">No Plan</Badge>
                    )}
                  </div>

                  {plan ? (
                    <div className="flex flex-wrap items-center gap-4">
                      <label className="text-sm text-muted-foreground">
                        Stage
                        <select
                          className="ml-2 rounded-md border border-border bg-background px-2 py-1 text-sm"
                          value={plan.stage}
                          onChange={(e) =>
                            handleUpdatePlan(plan.id, {
                              stage: e.target.value as CaptureStage,
                            })
                          }
                        >
                          {stageOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="text-sm text-muted-foreground">
                        Decision
                        <select
                          className="ml-2 rounded-md border border-border bg-background px-2 py-1 text-sm"
                          value={plan.bid_decision}
                          onChange={(e) =>
                            handleUpdatePlan(plan.id, {
                              bid_decision: e.target.value as BidDecision,
                            })
                          }
                        >
                          {decisionOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <span className="text-sm text-muted-foreground">
                        Win Probability: {plan.win_probability ?? "N/A"}%
                      </span>
                    </div>
                  ) : (
                    <Button onClick={() => handleCreatePlan(rfp.id)}>
                      Create Capture Plan
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6 mt-6">
          <div className="bg-card border border-border rounded-lg p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-foreground">Gate Reviews</p>
                <p className="text-xs text-muted-foreground">
                  Track bid/no-bid decisions
                </p>
              </div>
              <select
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                value={selectedRfpId ?? ""}
                onChange={(e) => setSelectedRfpId(Number(e.target.value))}
              >
                {rfps.map((rfp) => (
                  <option key={rfp.id} value={rfp.id}>
                    {rfp.title}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <select
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                value={gateReviewStage}
                onChange={(e) =>
                  setGateReviewStage(e.target.value as CaptureStage)
                }
              >
                {stageOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <select
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                value={gateReviewDecision}
                onChange={(e) =>
                  setGateReviewDecision(e.target.value as BidDecision)
                }
              >
                {decisionOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <input
                className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Notes"
                value={gateReviewNotes}
                onChange={(e) => setGateReviewNotes(e.target.value)}
              />
              <Button onClick={handleCreateGateReview}>Add Review</Button>
            </div>

            <div className="space-y-2">
              {gateReviews.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No gate reviews yet.
                </p>
              ) : (
                gateReviews.map((review) => (
                  <div
                    key={review.id}
                    className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                  >
                    <div>
                      <p className="font-medium text-foreground">
                        {review.stage} · {review.decision}
                      </p>
                      {review.notes && (
                        <p className="text-xs text-muted-foreground">
                          {review.notes}
                        </p>
                      )}
                    </div>
                    <Badge variant="outline">{review.created_at.slice(0, 10)}</Badge>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="bg-card border border-border rounded-lg p-4 space-y-4">
            <div>
              <p className="text-sm font-medium text-foreground">Teaming Partners</p>
              <p className="text-xs text-muted-foreground">
                Maintain partner list and link to opportunities
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <input
                className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Partner name"
                value={partnerName}
                onChange={(e) => setPartnerName(e.target.value)}
              />
              <input
                className="w-40 rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Type (prime/sub)"
                value={partnerType}
                onChange={(e) => setPartnerType(e.target.value)}
              />
              <Button onClick={handleCreatePartner}>Add Partner</Button>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <select
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                value={selectedRfpId ?? ""}
                onChange={(e) => setSelectedRfpId(Number(e.target.value))}
              >
                {rfps.map((rfp) => (
                  <option key={rfp.id} value={rfp.id}>
                    {rfp.title}
                  </option>
                ))}
              </select>
              <select
                className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                value={linkPartnerId ?? ""}
                onChange={(e) => setLinkPartnerId(Number(e.target.value))}
              >
                <option value="">Select partner</option>
                {partners.map((partner) => (
                  <option key={partner.id} value={partner.id}>
                    {partner.name}
                  </option>
                ))}
              </select>
              <input
                className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Role (Subcontractor)"
                value={linkRole}
                onChange={(e) => setLinkRole(e.target.value)}
              />
              <Button onClick={handleLinkPartner}>Link</Button>
            </div>

            <div className="space-y-2">
              {partnerLinks.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No partners linked to this opportunity.
                </p>
              ) : (
                partnerLinks.map((link) => {
                  const partner = partnerById.get(link.partner_id);
                  return (
                    <div
                      key={link.id}
                      className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                    >
                      <div>
                        <p className="font-medium text-foreground">
                          {partner?.name || "Unknown Partner"}
                        </p>
                        {link.role && (
                          <p className="text-xs text-muted-foreground">{link.role}</p>
                        )}
                      </div>
                      <Badge variant="outline">
                        {partner?.partner_type || "Partner"}
                      </Badge>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
