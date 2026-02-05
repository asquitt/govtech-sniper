"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, History, FileText } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { draftApi, versionApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { Proposal } from "@/types";
import type { ProposalVersion } from "@/lib/api";

type ProposalVersionDetail = ProposalVersion & {
  snapshot?: Record<string, unknown>;
  section_id?: number | null;
  section_snapshot?: Record<string, unknown> | null;
};

export default function ProposalVersionsPage() {
  const params = useParams();
  const proposalId = parseInt(params.proposalId as string, 10);

  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [versions, setVersions] = useState<ProposalVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [versionDetail, setVersionDetail] = useState<ProposalVersionDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const snapshotFields = useMemo(
    () => [
      { label: "Title", key: "title" },
      { label: "Status", key: "status" },
      { label: "Total Sections", key: "total_sections" },
      { label: "Completed", key: "completed_sections" },
      { label: "Compliance Score", key: "compliance_score" },
    ],
    []
  );

  const fetchVersions = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [proposalData, versionList] = await Promise.all([
        draftApi.getProposal(proposalId),
        versionApi.listProposalVersions(proposalId),
      ]);
      setProposal(proposalData);
      setVersions(versionList);
      if (versionList.length > 0) {
        setSelectedVersionId(versionList[0].id);
      }
    } catch (err) {
      console.error("Failed to load versions", err);
      setError("Failed to load proposal versions.");
    } finally {
      setIsLoading(false);
    }
  }, [proposalId]);

  useEffect(() => {
    fetchVersions();
  }, [fetchVersions]);

  useEffect(() => {
    const fetchDetail = async () => {
      if (!selectedVersionId) {
        setVersionDetail(null);
        return;
      }

      try {
        setIsDetailLoading(true);
        const detail = await versionApi.getProposalVersion(proposalId, selectedVersionId);
        setVersionDetail(detail);
      } catch (err) {
        console.error("Failed to load version detail", err);
        setVersionDetail(null);
      } finally {
        setIsDetailLoading(false);
      }
    };

    fetchDetail();
  }, [proposalId, selectedVersionId]);

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Proposal Versions" description="Loading version history" />
        <div className="flex-1 flex items-center justify-center">Loading...</div>
      </div>
    );
  }

  if (error || !proposal) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Proposal Versions" description="Unable to load proposal" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={fetchVersions}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Proposal Versions"
        description={`${proposal.title} • Version history`}
        actions={
          <Button variant="outline" asChild>
            <Link href={`/proposals/${proposalId}`}>
              <ArrowLeft className="w-4 h-4" />
              Back to Workspace
            </Link>
          </Button>
        }
      />

      <div className="flex-1 p-6 overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] gap-6 h-full">
          <Card className="border border-border h-full">
            <CardContent className="p-4 h-full flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-semibold text-foreground">Versions</p>
                  <p className="text-xs text-muted-foreground">
                    {versions.length} total snapshots
                  </p>
                </div>
              </div>
              <ScrollArea className="flex-1 -mx-2 px-2">
                <div className="space-y-2">
                  {versions.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No versions yet.</p>
                  ) : (
                    versions.map((version) => (
                      <button
                        key={version.id}
                        type="button"
                        className={`w-full text-left rounded-lg border px-3 py-2 transition-colors ${
                          selectedVersionId === version.id
                            ? "border-primary bg-primary/10"
                            : "border-border hover:border-primary/30"
                        }`}
                        onClick={() => setSelectedVersionId(version.id)}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium">
                              Version {version.version_number}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {version.description}
                            </p>
                          </div>
                          <History className="w-4 h-4 text-muted-foreground" />
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">
                          {formatDate(version.created_at)} • {version.version_type}
                        </p>
                      </button>
                    ))
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          <Card className="border border-border h-full">
            <CardContent className="p-4 h-full flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-semibold text-foreground">Snapshot Detail</p>
                  <p className="text-xs text-muted-foreground">
                    {versionDetail ? `Version ${versionDetail.version_number}` : "Select a version"}
                  </p>
                </div>
                {isDetailLoading && (
                  <span className="text-xs text-muted-foreground">Loading...</span>
                )}
              </div>

              {!versionDetail ? (
                <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
                  Select a version to see snapshot details.
                </div>
              ) : (
                <ScrollArea className="flex-1 -mx-2 px-2">
                  <div className="space-y-4">
                    <div className="rounded-lg border border-border p-3 space-y-2">
                      <p className="text-sm font-medium flex items-center gap-2">
                        <FileText className="w-4 h-4 text-muted-foreground" />
                        Proposal Snapshot
                      </p>
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        {snapshotFields.map((field) => (
                          <div key={field.key}>
                            <p className="text-muted-foreground">{field.label}</p>
                            <p>
                              {versionDetail.snapshot?.[field.key] !== undefined
                                ? String(versionDetail.snapshot?.[field.key])
                                : "—"}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>

                    {versionDetail.section_snapshot && (
                      <div className="rounded-lg border border-border p-3 space-y-2">
                        <p className="text-sm font-medium">Section Snapshot</p>
                        <pre className="text-xs whitespace-pre-wrap text-muted-foreground">
                          {JSON.stringify(versionDetail.section_snapshot, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
