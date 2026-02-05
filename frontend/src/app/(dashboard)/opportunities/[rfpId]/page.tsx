"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Calendar,
  Building2,
  ExternalLink,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { awardApi, contactApi, rfpApi, budgetIntelApi } from "@/lib/api";
import { cn, daysUntilDeadline, formatDate, getDeadlineUrgency } from "@/lib/utils";
import type { AwardRecord, OpportunityContact, RFP, RFPStatus, BudgetIntelligence } from "@/types";

type Snapshot = {
  id: number;
  notice_id: string;
  solicitation_number?: string | null;
  rfp_id: number;
  user_id?: number | null;
  fetched_at: string;
  posted_date?: string | null;
  response_deadline?: string | null;
  raw_hash: string;
  summary: Record<string, unknown>;
  raw_payload?: Record<string, unknown> | null;
};

type SnapshotDiff = {
  from_snapshot_id: number;
  to_snapshot_id: number;
  changes: { field: string; before?: string | null; after?: string | null }[];
  summary_from: Record<string, unknown>;
  summary_to: Record<string, unknown>;
};

const statusConfig: Record<
  RFPStatus,
  { label: string; variant: "default" | "success" | "warning" | "destructive" }
> = {
  new: { label: "New", variant: "default" },
  analyzing: { label: "Analyzing", variant: "warning" },
  analyzed: { label: "Analyzed", variant: "success" },
  drafting: { label: "Drafting", variant: "warning" },
  ready: { label: "Ready", variant: "success" },
  submitted: { label: "Submitted", variant: "success" },
  archived: { label: "Archived", variant: "destructive" },
};

function DeadlineBadge({ deadline }: { deadline?: string }) {
  const days = daysUntilDeadline(deadline);
  const urgency = getDeadlineUrgency(deadline);

  if (days === null) return <span className="text-muted-foreground">—</span>;

  const colorClass =
    urgency === "urgent"
      ? "text-destructive"
      : urgency === "warning"
      ? "text-warning"
      : "text-foreground";

  return (
    <span className={cn("flex items-center gap-1", colorClass)}>
      {urgency === "urgent" && <AlertTriangle className="w-3 h-3" />}
      {days < 0 ? "Overdue" : days === 0 ? "Today" : `${days} days`}
    </span>
  );
}

function formatSummaryValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return value.toString();
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

export default function OpportunityDetailPage() {
  const params = useParams();
  const rfpId = parseInt(params.rfpId as string, 10);

  const [rfp, setRfp] = useState<RFP | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [diff, setDiff] = useState<SnapshotDiff | null>(null);
  const [fromSnapshotId, setFromSnapshotId] = useState<number | null>(null);
  const [toSnapshotId, setToSnapshotId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "changes">("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [isDiffLoading, setIsDiffLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [awards, setAwards] = useState<AwardRecord[]>([]);
  const [contacts, setContacts] = useState<OpportunityContact[]>([]);
  const [budgetRecords, setBudgetRecords] = useState<BudgetIntelligence[]>([]);
  const [awardForm, setAwardForm] = useState({
    awardee_name: "",
    award_amount: "",
    award_date: "",
    contract_vehicle: "",
    contract_number: "",
    description: "",
    source_url: "",
  });
  const [budgetForm, setBudgetForm] = useState({
    title: "",
    fiscal_year: "",
    amount: "",
    source_url: "",
    notes: "",
  });
  const [contactForm, setContactForm] = useState({
    name: "",
    role: "",
    organization: "",
    email: "",
    phone: "",
    notes: "",
  });
  const [isSavingAward, setIsSavingAward] = useState(false);
  const [isSavingContact, setIsSavingContact] = useState(false);
  const [isSavingBudget, setIsSavingBudget] = useState(false);
  const [intelForm, setIntelForm] = useState({
    source_type: "",
    jurisdiction: "",
    contract_vehicle: "",
    incumbent_vendor: "",
    buyer_contact_name: "",
    buyer_contact_email: "",
    buyer_contact_phone: "",
    budget_estimate: "",
    competitive_landscape: "",
    intel_notes: "",
  });
  const [isSavingIntel, setIsSavingIntel] = useState(false);

  const summaryFields = useMemo(
    () => [
      { label: "Title", key: "title" },
      { label: "Agency", key: "agency" },
      { label: "Sub-Agency", key: "sub_agency" },
      { label: "NAICS", key: "naics_code" },
      { label: "Set-Aside", key: "set_aside" },
      { label: "Posted", key: "posted_date" },
      { label: "Deadline", key: "response_deadline" },
      { label: "Type", key: "rfp_type" },
      { label: "Resources", key: "resource_links_count" },
    ],
    []
  );

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [rfpData, snapshotData, awardData, contactData, budgetData] = await Promise.all([
        rfpApi.get(rfpId),
        rfpApi.getSnapshots(rfpId, { limit: 20 }),
        awardApi.list({ rfp_id: rfpId }),
        contactApi.list({ rfp_id: rfpId }),
        budgetIntelApi.list({ rfp_id: rfpId }),
      ]);
      setRfp(rfpData);
      setSnapshots(snapshotData);
      setAwards(awardData);
      setContacts(contactData);
      setBudgetRecords(budgetData);

      if (snapshotData.length >= 2) {
        setToSnapshotId(snapshotData[0].id);
        setFromSnapshotId(snapshotData[1].id);
      } else if (snapshotData.length === 1) {
        setToSnapshotId(snapshotData[0].id);
        setFromSnapshotId(null);
      } else {
        setToSnapshotId(null);
        setFromSnapshotId(null);
      }
    } catch (err) {
      console.error("Failed to load opportunity", err);
      setError("Failed to load opportunity data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [rfpId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!rfp) return;
    setIntelForm({
      source_type: rfp.source_type || "",
      jurisdiction: rfp.jurisdiction || "",
      contract_vehicle: rfp.contract_vehicle || "",
      incumbent_vendor: rfp.incumbent_vendor || "",
      buyer_contact_name: rfp.buyer_contact_name || "",
      buyer_contact_email: rfp.buyer_contact_email || "",
      buyer_contact_phone: rfp.buyer_contact_phone || "",
      budget_estimate: rfp.budget_estimate ? String(rfp.budget_estimate) : "",
      competitive_landscape: rfp.competitive_landscape || "",
      intel_notes: rfp.intel_notes || "",
    });
  }, [rfp]);

  const handleIntelChange = (field: keyof typeof intelForm, value: string) => {
    setIntelForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveIntel = async () => {
    if (!rfp) return;
    try {
      setIsSavingIntel(true);
      const payload = {
        source_type: intelForm.source_type || null,
        jurisdiction: intelForm.jurisdiction || null,
        contract_vehicle: intelForm.contract_vehicle || null,
        incumbent_vendor: intelForm.incumbent_vendor || null,
        buyer_contact_name: intelForm.buyer_contact_name || null,
        buyer_contact_email: intelForm.buyer_contact_email || null,
        buyer_contact_phone: intelForm.buyer_contact_phone || null,
        budget_estimate: intelForm.budget_estimate
          ? Number(intelForm.budget_estimate)
          : null,
        competitive_landscape: intelForm.competitive_landscape || null,
        intel_notes: intelForm.intel_notes || null,
      };
      const updated = await rfpApi.update(rfp.id, payload);
      setRfp(updated);
    } catch (saveErr) {
      console.error("Failed to save market intelligence", saveErr);
      setError("Failed to save market intelligence.");
    } finally {
      setIsSavingIntel(false);
    }
  };

  const handleAwardChange = (field: keyof typeof awardForm, value: string) => {
    setAwardForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleContactChange = (field: keyof typeof contactForm, value: string) => {
    setContactForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleBudgetChange = (field: keyof typeof budgetForm, value: string) => {
    setBudgetForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreateAward = async () => {
    if (!rfp || !awardForm.awardee_name.trim()) return;
    try {
      setIsSavingAward(true);
      const payload = {
        rfp_id: rfp.id,
        awardee_name: awardForm.awardee_name.trim(),
        award_amount: awardForm.award_amount
          ? Number(awardForm.award_amount)
          : undefined,
        award_date: awardForm.award_date || undefined,
        contract_vehicle: awardForm.contract_vehicle || undefined,
        contract_number: awardForm.contract_number || undefined,
        description: awardForm.description || undefined,
        source_url: awardForm.source_url || undefined,
      };
      const created = await awardApi.create(payload);
      setAwards((prev) => [created, ...prev]);
      setAwardForm({
        awardee_name: "",
        award_amount: "",
        award_date: "",
        contract_vehicle: "",
        contract_number: "",
        description: "",
        source_url: "",
      });
    } catch (err) {
      console.error("Failed to create award record", err);
      setError("Failed to create award record.");
    } finally {
      setIsSavingAward(false);
    }
  };

  const handleCreateContact = async () => {
    if (!rfp || !contactForm.name.trim()) return;
    try {
      setIsSavingContact(true);
      const payload = {
        rfp_id: rfp.id,
        name: contactForm.name.trim(),
        role: contactForm.role || undefined,
        organization: contactForm.organization || undefined,
        email: contactForm.email || undefined,
        phone: contactForm.phone || undefined,
        notes: contactForm.notes || undefined,
      };
      const created = await contactApi.create(payload);
      setContacts((prev) => [created, ...prev]);
      setContactForm({
        name: "",
        role: "",
        organization: "",
        email: "",
        phone: "",
        notes: "",
      });
    } catch (err) {
      console.error("Failed to create contact", err);
      setError("Failed to create contact.");
    } finally {
      setIsSavingContact(false);
    }
  };

  const handleCreateBudget = async () => {
    if (!rfp || !budgetForm.title.trim()) return;
    try {
      setIsSavingBudget(true);
      const created = await budgetIntelApi.create({
        rfp_id: rfp.id,
        title: budgetForm.title.trim(),
        fiscal_year: budgetForm.fiscal_year
          ? Number(budgetForm.fiscal_year)
          : undefined,
        amount: budgetForm.amount ? Number(budgetForm.amount) : undefined,
        source_url: budgetForm.source_url || undefined,
        notes: budgetForm.notes || undefined,
      });
      setBudgetRecords((prev) => [created, ...prev]);
      setBudgetForm({
        title: "",
        fiscal_year: "",
        amount: "",
        source_url: "",
        notes: "",
      });
    } catch (err) {
      console.error("Failed to create budget record", err);
      setError("Failed to create budget record.");
    } finally {
      setIsSavingBudget(false);
    }
  };

  useEffect(() => {
    const fetchDiff = async () => {
      if (!fromSnapshotId || !toSnapshotId || fromSnapshotId === toSnapshotId) {
        setDiff(null);
        return;
      }

      try {
        setIsDiffLoading(true);
        const diffData = await rfpApi.getSnapshotDiff(rfpId, {
          from_snapshot_id: fromSnapshotId,
          to_snapshot_id: toSnapshotId,
        });
        setDiff(diffData);
      } catch (diffErr) {
        console.error("Failed to load snapshot diff", diffErr);
        setDiff(null);
      } finally {
        setIsDiffLoading(false);
      }
    };

    fetchDiff();
  }, [fromSnapshotId, toSnapshotId, rfpId]);

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Opportunity" description="Loading opportunity details" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-muted-foreground">Loading...</div>
        </div>
      </div>
    );
  }

  if (error || !rfp) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Opportunity" description="Unable to load opportunity" />
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
        title={rfp.title}
        description={`${rfp.agency} • ${rfp.solicitation_number || rfp.id}`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" asChild>
              <Link href="/opportunities">
                <ArrowLeft className="w-4 h-4" />
                Back
              </Link>
            </Button>
            <Button asChild>
              <Link href={`/analysis/${rfp.id}`}>Analyze</Link>
            </Button>
            {rfp.sam_gov_link && (
              <Button variant="outline" asChild>
                <a href={rfp.sam_gov_link} target="_blank" rel="noreferrer">
                  <ExternalLink className="w-4 h-4" />
                  SAM.gov
                </a>
              </Button>
            )}
          </div>
        }
      />

      <div className="flex-1 p-6 overflow-auto space-y-6">
        <div className="flex items-center gap-2">
          <Button
            variant={activeTab === "overview" ? "default" : "outline"}
            onClick={() => setActiveTab("overview")}
          >
            Overview
          </Button>
          <Button
            variant={activeTab === "changes" ? "default" : "outline"}
            onClick={() => setActiveTab("changes")}
          >
            Changes
          </Button>
        </div>

        {activeTab === "overview" && (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <Card className="border border-border">
                <CardContent className="p-4 space-y-2">
                  <p className="text-xs text-muted-foreground">Status</p>
                  <Badge variant={statusConfig[rfp.status]?.variant || "default"}>
                    {statusConfig[rfp.status]?.label || rfp.status}
                  </Badge>
                </CardContent>
              </Card>
              <Card className="border border-border">
                <CardContent className="p-4 space-y-2">
                  <p className="text-xs text-muted-foreground">Qualification</p>
                  {rfp.is_qualified ? (
                    <div className="flex items-center gap-2 text-sm">
                      <CheckCircle2 className="w-4 h-4 text-success" />
                      Qualified ({rfp.qualification_score ?? 0}% match)
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-sm">
                      <Clock className="w-4 h-4 text-warning" />
                      Pending qualification
                    </div>
                  )}
                </CardContent>
              </Card>
              <Card className="border border-border">
                <CardContent className="p-4 space-y-2">
                  <p className="text-xs text-muted-foreground">Deadline</p>
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <DeadlineBadge deadline={rfp.response_deadline} />
                      <p className="text-xs text-muted-foreground">
                        {formatDate(rfp.response_deadline)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Card className="border border-border">
                <CardContent className="p-4 space-y-3">
                  <p className="text-sm font-medium">Summary</p>
                  <p className="text-sm text-muted-foreground whitespace-pre-line">
                    {rfp.summary || rfp.description || "No summary available."}
                  </p>
                </CardContent>
              </Card>
              <Card className="border border-border">
                <CardContent className="p-4 space-y-3">
                  <p className="text-sm font-medium">Opportunity Details</p>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-muted-foreground" />
                      <span>{rfp.agency}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-muted-foreground" />
                      <span>{rfp.solicitation_number || rfp.id}</span>
                    </div>
                    <div>
                      <span className="text-xs text-muted-foreground">NAICS</span>
                      <p>{rfp.naics_code || "—"}</p>
                    </div>
                    <div>
                      <span className="text-xs text-muted-foreground">Set-Aside</span>
                      <p>{rfp.set_aside || "—"}</p>
                    </div>
                    <div>
                      <span className="text-xs text-muted-foreground">Estimated Value</span>
                      <p>
                        {rfp.estimated_value
                          ? `$${rfp.estimated_value.toLocaleString()}`
                          : "—"}
                      </p>
                    </div>
                    <div>
                      <span className="text-xs text-muted-foreground">
                        Place of Performance
                      </span>
                      <p>{rfp.place_of_performance || "—"}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="border border-border">
              <CardContent className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Market Intelligence</p>
                    <p className="text-xs text-muted-foreground">
                      Track vehicles, incumbents, buyer contacts, and competitive context.
                    </p>
                  </div>
                  <Button size="sm" onClick={handleSaveIntel} disabled={isSavingIntel}>
                    {isSavingIntel ? "Saving..." : "Save Intel"}
                  </Button>
                </div>

                <div className="grid gap-3 md:grid-cols-3 text-sm">
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Source Type (federal, sled)"
                    value={intelForm.source_type}
                    onChange={(e) => handleIntelChange("source_type", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Jurisdiction (e.g., VA)"
                    value={intelForm.jurisdiction}
                    onChange={(e) => handleIntelChange("jurisdiction", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Contract Vehicle"
                    value={intelForm.contract_vehicle}
                    onChange={(e) => handleIntelChange("contract_vehicle", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Incumbent Vendor"
                    value={intelForm.incumbent_vendor}
                    onChange={(e) => handleIntelChange("incumbent_vendor", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Budget Estimate"
                    value={intelForm.budget_estimate}
                    onChange={(e) => handleIntelChange("budget_estimate", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Buyer Contact Name"
                    value={intelForm.buyer_contact_name}
                    onChange={(e) => handleIntelChange("buyer_contact_name", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Buyer Contact Email"
                    value={intelForm.buyer_contact_email}
                    onChange={(e) => handleIntelChange("buyer_contact_email", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Buyer Contact Phone"
                    value={intelForm.buyer_contact_phone}
                    onChange={(e) => handleIntelChange("buyer_contact_phone", e.target.value)}
                  />
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <textarea
                    className="min-h-[100px] rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Competitive landscape notes"
                    value={intelForm.competitive_landscape}
                    onChange={(e) =>
                      handleIntelChange("competitive_landscape", e.target.value)
                    }
                  />
                  <textarea
                    className="min-h-[100px] rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Additional intel notes"
                    value={intelForm.intel_notes}
                    onChange={(e) => handleIntelChange("intel_notes", e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardContent className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Budget Intelligence</p>
                    <p className="text-xs text-muted-foreground">
                      Track funding signals tied to this opportunity.
                    </p>
                  </div>
                  <Button size="sm" onClick={handleCreateBudget} disabled={isSavingBudget}>
                    {isSavingBudget ? "Saving..." : "Add Budget"}
                  </Button>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Budget title"
                    value={budgetForm.title}
                    onChange={(e) => handleBudgetChange("title", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Fiscal year"
                    value={budgetForm.fiscal_year}
                    onChange={(e) => handleBudgetChange("fiscal_year", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Amount"
                    value={budgetForm.amount}
                    onChange={(e) => handleBudgetChange("amount", e.target.value)}
                  />
                </div>

                <input
                  className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                  placeholder="Source URL"
                  value={budgetForm.source_url}
                  onChange={(e) => handleBudgetChange("source_url", e.target.value)}
                />

                <textarea
                  className="min-h-[80px] rounded-md border border-border bg-background px-2 py-1 text-sm"
                  placeholder="Budget notes"
                  value={budgetForm.notes}
                  onChange={(e) => handleBudgetChange("notes", e.target.value)}
                />

                {budgetRecords.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No budget intel recorded yet.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {budgetRecords.map((record) => (
                      <div
                        key={record.id}
                        className="rounded-md border border-border px-3 py-2 text-sm"
                      >
                        <p className="font-medium text-foreground">{record.title}</p>
                        <p className="text-xs text-muted-foreground">
                          FY {record.fiscal_year || "—"} ·{" "}
                          {record.amount
                            ? `$${record.amount.toLocaleString()}`
                            : "Amount TBD"}
                        </p>
                        {record.source_url && (
                          <p className="text-xs text-primary break-all">
                            {record.source_url}
                          </p>
                        )}
                        {record.notes && (
                          <p className="text-xs text-muted-foreground">
                            {record.notes}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardContent className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Award Intelligence</p>
                    <p className="text-xs text-muted-foreground">
                      Track awardees, values, and vehicles tied to this opportunity.
                    </p>
                  </div>
                  <Button size="sm" onClick={handleCreateAward} disabled={isSavingAward}>
                    {isSavingAward ? "Saving..." : "Add Award"}
                  </Button>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Awardee Name"
                    value={awardForm.awardee_name}
                    onChange={(e) => handleAwardChange("awardee_name", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Award Amount"
                    value={awardForm.award_amount}
                    onChange={(e) => handleAwardChange("award_amount", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Award Date (YYYY-MM-DD)"
                    value={awardForm.award_date}
                    onChange={(e) => handleAwardChange("award_date", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Contract Vehicle"
                    value={awardForm.contract_vehicle}
                    onChange={(e) => handleAwardChange("contract_vehicle", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Contract Number"
                    value={awardForm.contract_number}
                    onChange={(e) => handleAwardChange("contract_number", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Source URL"
                    value={awardForm.source_url}
                    onChange={(e) => handleAwardChange("source_url", e.target.value)}
                  />
                </div>

                <textarea
                  className="min-h-[80px] rounded-md border border-border bg-background px-2 py-1 text-sm"
                  placeholder="Award description or notes"
                  value={awardForm.description}
                  onChange={(e) => handleAwardChange("description", e.target.value)}
                />

                {awards.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No awards recorded yet.</p>
                ) : (
                  <div className="space-y-2">
                    {awards.map((award) => (
                      <div
                        key={award.id}
                        className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                      >
                        <div>
                          <p className="font-medium text-foreground">
                            {award.awardee_name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {award.award_amount
                              ? `$${award.award_amount.toLocaleString()}`
                              : "—"}{" "}
                            · {award.contract_vehicle || "Vehicle unknown"}
                          </p>
                        </div>
                        <Badge variant="outline">
                          {award.award_date ? formatDate(award.award_date) : "Date TBD"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardContent className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Opportunity Contacts</p>
                    <p className="text-xs text-muted-foreground">
                      Track buyers, stakeholders, and partner contacts.
                    </p>
                  </div>
                  <Button
                    size="sm"
                    onClick={handleCreateContact}
                    disabled={isSavingContact}
                  >
                    {isSavingContact ? "Saving..." : "Add Contact"}
                  </Button>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Name"
                    value={contactForm.name}
                    onChange={(e) => handleContactChange("name", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Role"
                    value={contactForm.role}
                    onChange={(e) => handleContactChange("role", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Organization"
                    value={contactForm.organization}
                    onChange={(e) => handleContactChange("organization", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Email"
                    value={contactForm.email}
                    onChange={(e) => handleContactChange("email", e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Phone"
                    value={contactForm.phone}
                    onChange={(e) => handleContactChange("phone", e.target.value)}
                  />
                </div>

                <textarea
                  className="min-h-[80px] rounded-md border border-border bg-background px-2 py-1 text-sm"
                  placeholder="Contact notes"
                  value={contactForm.notes}
                  onChange={(e) => handleContactChange("notes", e.target.value)}
                />

                {contacts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No contacts yet.</p>
                ) : (
                  <div className="space-y-2">
                    {contacts.map((contact) => (
                      <div
                        key={contact.id}
                        className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                      >
                        <div>
                          <p className="font-medium text-foreground">{contact.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {contact.role || "Role unknown"} · {contact.organization || "Org"}
                          </p>
                        </div>
                        <Badge variant="outline">
                          {contact.email || contact.phone || "No contact info"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardContent className="p-4 space-y-2">
                <p className="text-sm font-medium">Source Links</p>
                <div className="space-y-2 text-sm">
                  {rfp.source_url && (
                    <a
                      href={rfp.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-2 text-primary hover:underline"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Source URL
                    </a>
                  )}
                  {rfp.sam_gov_link && (
                    <a
                      href={rfp.sam_gov_link}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-2 text-primary hover:underline"
                    >
                      <ExternalLink className="w-4 h-4" />
                      SAM.gov Link
                    </a>
                  )}
                  {!rfp.source_url && !rfp.sam_gov_link && (
                    <p className="text-muted-foreground">No links available.</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "changes" && (
          <div className="grid gap-6 lg:grid-cols-[2fr_3fr]">
            <Card className="border border-border">
              <CardContent className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">Snapshots</p>
                  <span className="text-xs text-muted-foreground">
                    {snapshots.length} total
                  </span>
                </div>
                {snapshots.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No snapshots available.</p>
                ) : (
                  <ScrollArea className="h-[420px] pr-2">
                    <div className="space-y-3">
                      {snapshots.map((snapshot) => (
                        <div
                          key={snapshot.id}
                          className="rounded-lg border border-border p-3 text-xs space-y-2"
                        >
                          <div className="flex items-center justify-between">
                            <p className="font-medium">Snapshot {snapshot.id}</p>
                            <span className="text-muted-foreground">
                              {formatDate(snapshot.fetched_at)}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            {summaryFields.map((field) => (
                              <div key={`${snapshot.id}-${field.key}`}>
                                <p className="text-muted-foreground">{field.label}</p>
                                <p>{formatSummaryValue(snapshot.summary[field.key])}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardContent className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Snapshot Diff</p>
                    <p className="text-xs text-muted-foreground">
                      Compare any two snapshots for changes
                    </p>
                  </div>
                  {isDiffLoading && (
                    <span className="text-xs text-muted-foreground">Loading...</span>
                  )}
                </div>

                {snapshots.length < 2 ? (
                  <p className="text-sm text-muted-foreground">
                    At least two snapshots are required to view changes.
                  </p>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2">
                    <label className="text-xs text-muted-foreground">
                      From Snapshot
                      <select
                        className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                        value={fromSnapshotId ?? ""}
                        onChange={(e) => setFromSnapshotId(Number(e.target.value))}
                      >
                        {snapshots.map((snapshot) => (
                          <option key={snapshot.id} value={snapshot.id}>
                            {snapshot.id} ({formatDate(snapshot.fetched_at)})
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-xs text-muted-foreground">
                      To Snapshot
                      <select
                        className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                        value={toSnapshotId ?? ""}
                        onChange={(e) => setToSnapshotId(Number(e.target.value))}
                      >
                        {snapshots.map((snapshot) => (
                          <option key={snapshot.id} value={snapshot.id}>
                            {snapshot.id} ({formatDate(snapshot.fetched_at)})
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                )}

                {diff && diff.changes.length > 0 ? (
                  <div className="space-y-3">
                    {diff.changes.map((change, index) => (
                      <div
                        key={`${change.field}-${index}`}
                        className="grid grid-cols-3 gap-3 text-xs border border-border rounded-lg p-3"
                      >
                        <div className="text-muted-foreground">
                          <span className="font-medium text-foreground">
                            {change.field}
                          </span>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Before</p>
                          <p className="text-foreground">
                            {change.before || "—"}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">After</p>
                          <p className="text-foreground">
                            {change.after || "—"}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {snapshots.length >= 2
                      ? "No changes detected for selected snapshots."
                      : ""}
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
