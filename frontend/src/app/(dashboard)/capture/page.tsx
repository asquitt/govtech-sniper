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
  RFP,
  CaptureCustomField,
  CaptureFieldType,
  CaptureFieldValue,
  CaptureCompetitor,
  CaptureMatchInsight,
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
  const [selectedRfp, setSelectedRfp] = useState<RFP | null>(null);
  const [customFields, setCustomFields] = useState<CaptureCustomField[]>([]);
  const [planFieldValues, setPlanFieldValues] = useState<CaptureFieldValue[]>([]);
  const [matchInsight, setMatchInsight] = useState<CaptureMatchInsight | null>(null);
  const [competitors, setCompetitors] = useState<CaptureCompetitor[]>([]);
  const [competitorName, setCompetitorName] = useState("");
  const [competitorStrengths, setCompetitorStrengths] = useState("");
  const [competitorWeaknesses, setCompetitorWeaknesses] = useState("");
  const [competitorIncumbent, setCompetitorIncumbent] = useState(false);
  const [competitorNotes, setCompetitorNotes] = useState("");
  const [customFieldName, setCustomFieldName] = useState("");
  const [customFieldType, setCustomFieldType] = useState<CaptureFieldType>("text");
  const [customFieldOptions, setCustomFieldOptions] = useState("");
  const [customFieldStage, setCustomFieldStage] = useState<CaptureStage | "">("");
  const [customFieldRequired, setCustomFieldRequired] = useState(false);
  const [partnerName, setPartnerName] = useState("");
  const [partnerType, setPartnerType] = useState("");
  const [linkPartnerId, setLinkPartnerId] = useState<number | null>(null);
  const [linkRole, setLinkRole] = useState("");
  const [gateReviewStage, setGateReviewStage] = useState<CaptureStage>("qualified");
  const [gateReviewDecision, setGateReviewDecision] =
    useState<BidDecision>("pending");
  const [gateReviewNotes, setGateReviewNotes] = useState("");
  const [viewMode, setViewMode] = useState<"list" | "kanban">("list");
  const [isSavingFields, setIsSavingFields] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [rfpList, planList, partnerList, fieldList] = await Promise.all([
        rfpApi.list({ limit: 100 }),
        captureApi.listPlans(),
        captureApi.listPartners(),
        captureApi.listFields(),
      ]);
      setRfps(rfpList);
      setPlans(planList);
      setPartners(partnerList);
      setCustomFields(fieldList);
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

  const planByRfp = useMemo(() => {
    const map = new Map<number, CapturePlanListItem>();
    plans.forEach((plan) => map.set(plan.rfp_id, plan));
    return map;
  }, [plans]);

  const plansByStage = useMemo(() => {
    const map = new Map<CaptureStage, CapturePlanListItem[]>();
    stageOptions.forEach((option) => map.set(option.value, []));
    plans.forEach((plan) => {
      const bucket = map.get(plan.stage);
      if (bucket) {
        bucket.push(plan);
      } else {
        map.set(plan.stage, [plan]);
      }
    });
    return map;
  }, [plans]);

  useEffect(() => {
    const fetchRfpDetails = async () => {
      if (!selectedRfpId) {
        setSelectedRfp(null);
        setMatchInsight(null);
        setCompetitors([]);
        return;
      }
      try {
        const plan = planByRfp.get(selectedRfpId);
        const [linksResult, reviewsResult, fieldsResult, rfpDetail, competitorList, insight] =
          await Promise.all([
          captureApi.listPartnerLinks(selectedRfpId),
          captureApi.listGateReviews(selectedRfpId),
          plan ? captureApi.listPlanFields(plan.id) : Promise.resolve({ fields: [] }),
          rfpApi.get(selectedRfpId),
          captureApi.listCompetitors(selectedRfpId),
          plan ? captureApi.getMatchInsight(plan.id) : Promise.resolve(null),
        ]);
        setPartnerLinks(linksResult.links);
        setGateReviews(reviewsResult);
        setPlanFieldValues(fieldsResult.fields ?? []);
        setSelectedRfp(rfpDetail);
        setCompetitors(competitorList);
        setMatchInsight(insight);
      } catch (err) {
        console.error("Failed to load capture details", err);
      }
    };
    fetchRfpDetails();
  }, [selectedRfpId, planByRfp]);

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

  const handleCreateCustomField = async () => {
    if (!customFieldName.trim()) return;
    try {
      const options =
        customFieldType === "select"
          ? customFieldOptions
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean)
          : [];
      const field = await captureApi.createField({
        name: customFieldName.trim(),
        field_type: customFieldType,
        options,
        stage: customFieldStage || null,
        is_required: customFieldRequired,
      });
      setCustomFields((prev) => [...prev, field]);
      setCustomFieldName("");
      setCustomFieldOptions("");
      setCustomFieldStage("");
      setCustomFieldRequired(false);
    } catch (err) {
      console.error("Failed to create custom field", err);
      setError("Failed to create custom field.");
    }
  };

  const handleCreateCompetitor = async () => {
    if (!selectedRfpId || !competitorName.trim()) return;
    try {
      const created = await captureApi.createCompetitor({
        rfp_id: selectedRfpId,
        name: competitorName.trim(),
        incumbent: competitorIncumbent,
        strengths: competitorStrengths || undefined,
        weaknesses: competitorWeaknesses || undefined,
        notes: competitorNotes || undefined,
      });
      setCompetitors((prev) => [created, ...prev]);
      setCompetitorName("");
      setCompetitorStrengths("");
      setCompetitorWeaknesses("");
      setCompetitorNotes("");
      setCompetitorIncumbent(false);
    } catch (err) {
      console.error("Failed to create competitor", err);
      setError("Failed to create competitor.");
    }
  };

  const handleRemoveCompetitor = async (competitorId: number) => {
    try {
      await captureApi.removeCompetitor(competitorId);
      setCompetitors((prev) => prev.filter((item) => item.id !== competitorId));
    } catch (err) {
      console.error("Failed to remove competitor", err);
      setError("Failed to remove competitor.");
    }
  };

  const handleFieldValueChange = (fieldId: number, value: unknown) => {
    setPlanFieldValues((prev) =>
      prev.map((item) =>
        item.field.id === fieldId ? { ...item, value } : item
      )
    );
  };

  const handleSavePlanFields = async () => {
    const plan = selectedRfpId ? planByRfp.get(selectedRfpId) : null;
    if (!plan) return;
    try {
      setIsSavingFields(true);
      const updated = await captureApi.savePlanFields(plan.id, planFieldValues);
      setPlanFieldValues(updated.fields);
    } catch (err) {
      console.error("Failed to save custom fields", err);
      setError("Failed to save custom fields.");
    } finally {
      setIsSavingFields(false);
    }
  };

  const renderFieldControl = (item: CaptureFieldValue) => {
    const value = item.value ?? "";
    if (item.field.field_type === "select") {
      return (
        <select
          className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
          value={String(value)}
          onChange={(e) => handleFieldValueChange(item.field.id, e.target.value)}
        >
          <option value="">Select option</option>
          {item.field.options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      );
    }

    if (item.field.field_type === "boolean") {
      return (
        <select
          className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
          value={value === "" ? "" : String(value)}
          onChange={(e) =>
            handleFieldValueChange(
              item.field.id,
              e.target.value === "" ? "" : e.target.value === "true"
            )
          }
        >
          <option value="">Select</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      );
    }

    return (
      <input
        className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
        type={item.field.field_type === "date" ? "date" : "text"}
        value={String(value)}
        onChange={(e) =>
          handleFieldValueChange(
            item.field.id,
            item.field.field_type === "number"
              ? Number(e.target.value)
              : e.target.value
          )
        }
      />
    );
  };

  const partnerById = useMemo(() => {
    const map = new Map<number, TeamingPartner>();
    partners.forEach((partner) => map.set(partner.id, partner));
    return map;
  }, [partners]);

  const formatIntelValue = (value?: string | number | null) => {
    if (value === null || value === undefined || value === "") return "—";
    return String(value);
  };

  const formatBudget = (value?: number | null) => {
    if (value === null || value === undefined) return "—";
    return `$${value.toLocaleString()}`;
  };

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
          <div className="px-4 py-3 border-b border-border flex items-center justify-between text-sm font-medium">
            <span>Capture Pipeline</span>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant={viewMode === "list" ? "default" : "outline"}
                onClick={() => setViewMode("list")}
              >
                List
              </Button>
              <Button
                size="sm"
                variant={viewMode === "kanban" ? "default" : "outline"}
                onClick={() => setViewMode("kanban")}
              >
                Kanban
              </Button>
            </div>
          </div>

          {viewMode === "list" ? (
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
          ) : (
            <div className="grid gap-4 p-4 md:grid-cols-3 lg:grid-cols-4">
              {stageOptions.map((stage) => {
                const stagePlans = plansByStage.get(stage.value) || [];
                return (
                  <div
                    key={stage.value}
                    className="rounded-lg border border-border bg-background/40"
                  >
                    <div className="px-3 py-2 border-b border-border text-xs font-medium uppercase text-muted-foreground">
                      {stage.label} ({stagePlans.length})
                    </div>
                    <div className="space-y-2 p-3">
                      {stagePlans.length === 0 ? (
                        <p className="text-xs text-muted-foreground">
                          No plans in this stage.
                        </p>
                      ) : (
                        stagePlans.map((plan) => (
                          <div
                            key={plan.id}
                            className="rounded-md border border-border bg-card px-3 py-2 text-sm space-y-2"
                          >
                            <div>
                              <p className="font-medium text-foreground">
                                {plan.rfp_title || `RFP ${plan.rfp_id}`}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {plan.rfp_agency || "Unknown agency"}
                              </p>
                            </div>
                            <div className="flex items-center justify-between text-xs text-muted-foreground">
                              <span>Decision: {plan.bid_decision}</span>
                              <span>Win: {plan.win_probability ?? "N/A"}%</span>
                            </div>
                            <select
                              className="w-full rounded-md border border-border bg-background px-2 py-1 text-xs"
                              value={plan.stage}
                              onChange={(e) =>
                                handleUpdatePlan(plan.id, {
                                  stage: e.target.value as CaptureStage,
                                })
                              }
                            >
                              {stageOptions.map((option) => (
                                <option key={option.value} value={option.value}>
                                  Move to {option.label}
                                </option>
                              ))}
                            </select>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
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

        <div className="bg-card border border-border rounded-lg p-4 space-y-4 mt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-foreground">Competitive Intel</p>
              <p className="text-xs text-muted-foreground">
                Surface vehicles, incumbents, and buyer details for the selected opportunity.
              </p>
            </div>
            <Badge variant="outline">
              {selectedRfp?.source_type || "Source unknown"}
            </Badge>
          </div>

          {selectedRfp ? (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Jurisdiction</p>
                  <p className="text-foreground">
                    {formatIntelValue(selectedRfp.jurisdiction)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Contract Vehicle</p>
                  <p className="text-foreground">
                    {formatIntelValue(selectedRfp.contract_vehicle)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Incumbent Vendor</p>
                  <p className="text-foreground">
                    {formatIntelValue(selectedRfp.incumbent_vendor)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Budget Estimate</p>
                  <p className="text-foreground">
                    {formatBudget(selectedRfp.budget_estimate)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Buyer Contact</p>
                  <p className="text-foreground">
                    {formatIntelValue(selectedRfp.buyer_contact_name)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Buyer Email / Phone</p>
                  <p className="text-foreground">
                    {formatIntelValue(selectedRfp.buyer_contact_email)}
                    {selectedRfp.buyer_contact_phone
                      ? ` · ${selectedRfp.buyer_contact_phone}`
                      : ""}
                  </p>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-md border border-border bg-background/40 p-3">
                  <p className="text-xs text-muted-foreground mb-2">
                    Competitive Landscape
                  </p>
                  <p className="text-sm text-foreground whitespace-pre-line">
                    {formatIntelValue(selectedRfp.competitive_landscape)}
                  </p>
                </div>
                <div className="rounded-md border border-border bg-background/40 p-3">
                  <p className="text-xs text-muted-foreground mb-2">Intel Notes</p>
                  <p className="text-sm text-foreground whitespace-pre-line">
                    {formatIntelValue(selectedRfp.intel_notes)}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Select an opportunity to view competitive intel.
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-6 mt-6">
          <div className="bg-card border border-border rounded-lg p-4 space-y-4">
            <div>
              <p className="text-sm font-medium text-foreground">Bid Match Insight</p>
              <p className="text-xs text-muted-foreground">
                Summary of fit signals for the selected capture plan.
              </p>
            </div>
            {matchInsight ? (
              <div className="space-y-3 text-sm">
                <p className="text-foreground">{matchInsight.summary}</p>
                <div className="grid gap-2 md:grid-cols-2 text-xs text-muted-foreground">
                  {matchInsight.factors.map((factor, index) => (
                    <div key={`${factor.factor}-${index}`} className="rounded-md border border-border p-2">
                      <p className="text-foreground font-medium">{factor.factor}</p>
                      <p>{String(factor.value)}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Select a plan to view insight.</p>
            )}
          </div>

          <div className="bg-card border border-border rounded-lg p-4 space-y-4">
            <div>
              <p className="text-sm font-medium text-foreground">Competitor Comparisons</p>
              <p className="text-xs text-muted-foreground">
                Track incumbents and competitive positioning.
              </p>
            </div>

            <div className="space-y-2">
              {competitors.length === 0 ? (
                <p className="text-sm text-muted-foreground">No competitors tracked yet.</p>
              ) : (
                competitors.map((competitor) => (
                  <div
                    key={competitor.id}
                    className="rounded-md border border-border p-3 text-sm space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <p className="font-medium text-foreground">
                        {competitor.name}
                        {competitor.incumbent ? " (Incumbent)" : ""}
                      </p>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveCompetitor(competitor.id)}
                      >
                        Remove
                      </Button>
                    </div>
                    {competitor.strengths && (
                      <p className="text-xs text-muted-foreground">
                        Strengths: {competitor.strengths}
                      </p>
                    )}
                    {competitor.weaknesses && (
                      <p className="text-xs text-muted-foreground">
                        Weaknesses: {competitor.weaknesses}
                      </p>
                    )}
                    {competitor.notes && (
                      <p className="text-xs text-muted-foreground">
                        Notes: {competitor.notes}
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="space-y-2">
              <input
                className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Competitor name"
                value={competitorName}
                onChange={(e) => setCompetitorName(e.target.value)}
              />
              <textarea
                className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Strengths"
                value={competitorStrengths}
                onChange={(e) => setCompetitorStrengths(e.target.value)}
                rows={2}
              />
              <textarea
                className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Weaknesses"
                value={competitorWeaknesses}
                onChange={(e) => setCompetitorWeaknesses(e.target.value)}
                rows={2}
              />
              <textarea
                className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                placeholder="Notes"
                value={competitorNotes}
                onChange={(e) => setCompetitorNotes(e.target.value)}
                rows={2}
              />
              <label className="flex items-center gap-2 text-xs text-muted-foreground">
                <input
                  type="checkbox"
                  checked={competitorIncumbent}
                  onChange={(e) => setCompetitorIncumbent(e.target.checked)}
                />
                Incumbent
              </label>
              <Button onClick={handleCreateCompetitor}>Add Competitor</Button>
            </div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-4 space-y-4 mt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-foreground">Custom Fields</p>
              <p className="text-xs text-muted-foreground">
                Add capture-specific fields and set values per opportunity.
              </p>
            </div>
            <Button size="sm" onClick={handleSavePlanFields} disabled={isSavingFields}>
              {isSavingFields ? "Saving..." : "Save Values"}
            </Button>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <input
              className="rounded-md border border-border bg-background px-2 py-1 text-sm"
              placeholder="Field name"
              value={customFieldName}
              onChange={(e) => setCustomFieldName(e.target.value)}
            />
            <select
              className="rounded-md border border-border bg-background px-2 py-1 text-sm"
              value={customFieldType}
              onChange={(e) => setCustomFieldType(e.target.value as CaptureFieldType)}
            >
              <option value="text">Text</option>
              <option value="number">Number</option>
              <option value="select">Select</option>
              <option value="date">Date</option>
              <option value="boolean">Boolean</option>
            </select>
            <input
              className="rounded-md border border-border bg-background px-2 py-1 text-sm"
              placeholder="Options (comma-separated)"
              value={customFieldOptions}
              onChange={(e) => setCustomFieldOptions(e.target.value)}
              disabled={customFieldType !== "select"}
            />
            <select
              className="rounded-md border border-border bg-background px-2 py-1 text-sm"
              value={customFieldStage}
              onChange={(e) => setCustomFieldStage(e.target.value as CaptureStage | "")}
            >
              <option value="">Any Stage</option>
              {stageOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <input
                type="checkbox"
                checked={customFieldRequired}
                onChange={(e) => setCustomFieldRequired(e.target.checked)}
              />
              Required
            </label>
            <Button onClick={handleCreateCustomField}>Add Field</Button>
          </div>

          <div className="space-y-3">
            {planFieldValues.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No custom fields available for this plan.
              </p>
            ) : (
              planFieldValues.map((item) => (
                <div
                  key={item.field.id}
                  className="grid grid-cols-3 gap-3 items-center text-sm"
                >
                  <div>
                    <p className="font-medium text-foreground">{item.field.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {item.field.field_type} {item.field.is_required ? "· Required" : ""}
                    </p>
                  </div>
                  <div className="col-span-2">{renderFieldControl(item)}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
