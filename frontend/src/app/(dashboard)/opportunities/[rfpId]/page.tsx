"use client";

import React, { useCallback, useEffect, useState } from "react";
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
import { awardApi, contactApi, rfpApi, budgetIntelApi } from "@/lib/api";
import { cn, daysUntilDeadline, formatDate, getDeadlineUrgency } from "@/lib/utils";
import type { AwardRecord, OpportunityContact, RFP, RFPStatus, BudgetIntelligence } from "@/types";
import { MarketIntelForm } from "./_components/market-intel-form";
import { BudgetIntelSection } from "./_components/budget-intel-section";
import { AwardIntelSection } from "./_components/award-intel-section";
import { ContactsSection } from "./_components/contacts-section";
import { SnapshotDiffPanel } from "./_components/snapshot-diff-panel";
import type { Snapshot } from "./_components/snapshot-diff-panel";

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

  if (days === null) return <span className="text-muted-foreground">&mdash;</span>;

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

export default function OpportunityDetailPage() {
  const params = useParams();
  const rfpId = parseInt(params.rfpId as string, 10);

  const [rfp, setRfp] = useState<RFP | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [awards, setAwards] = useState<AwardRecord[]>([]);
  const [contacts, setContacts] = useState<OpportunityContact[]>([]);
  const [budgetRecords, setBudgetRecords] = useState<BudgetIntelligence[]>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "changes">("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
                      <p>{rfp.naics_code || "\u2014"}</p>
                    </div>
                    <div>
                      <span className="text-xs text-muted-foreground">Set-Aside</span>
                      <p>{rfp.set_aside || "\u2014"}</p>
                    </div>
                    <div>
                      <span className="text-xs text-muted-foreground">Estimated Value</span>
                      <p>
                        {rfp.estimated_value
                          ? `$${rfp.estimated_value.toLocaleString()}`
                          : "\u2014"}
                      </p>
                    </div>
                    <div>
                      <span className="text-xs text-muted-foreground">
                        Place of Performance
                      </span>
                      <p>{rfp.place_of_performance || "\u2014"}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <MarketIntelForm rfp={rfp} onUpdate={setRfp} onError={setError} />
            <BudgetIntelSection rfpId={rfp.id} initialRecords={budgetRecords} onError={setError} />
            <AwardIntelSection rfpId={rfp.id} initialAwards={awards} onError={setError} />
            <ContactsSection rfpId={rfp.id} initialContacts={contacts} onError={setError} />

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
          <SnapshotDiffPanel rfpId={rfpId} snapshots={snapshots} />
        )}
      </div>
    </div>
  );
}
