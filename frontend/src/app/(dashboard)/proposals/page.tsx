"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { draftApi } from "@/lib/api";
import type { Proposal } from "@/types";

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProposals = async () => {
      try {
        const list = await draftApi.listProposals();
        setProposals(list);
      } catch (err) {
        console.error("Failed to load proposals", err);
        setError("Failed to load proposals.");
      }
    };
    fetchProposals();
  }, []);

  return (
    <div className="flex flex-col h-full">
      <Header title="Proposals" description="Manage proposal drafts" />

      <div className="flex-1 p-6 overflow-auto">
        {error && <p className="text-destructive">{error}</p>}

        <div className="grid gap-4">
          {proposals.length === 0 ? (
            <Card className="border border-border">
              <CardContent className="p-6 text-sm text-muted-foreground">
                No proposals yet.
              </CardContent>
            </Card>
          ) : (
            proposals.map((proposal) => (
              <Card key={proposal.id} className="border border-border">
                <CardContent className="p-6 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">{proposal.title}</p>
                    <p className="text-xs text-muted-foreground">
                      Status: {proposal.status}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">
                      {Math.round(proposal.completion_percentage)}% complete
                    </Badge>
                    <Link
                      href={`/analysis/${proposal.rfp_id}`}
                      className="text-sm text-primary"
                    >
                      Open
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
