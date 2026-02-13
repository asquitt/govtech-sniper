"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CapabilityGapResult, TeamingPartnerPublicProfile } from "@/types";

interface PartnerResultsListProps {
  partners: TeamingPartnerPublicProfile[];
  loading: boolean;
  gapResult: CapabilityGapResult | null;
  onRequestTeaming: (partnerId: number) => void;
}

export function PartnerResultsList({
  partners,
  loading,
  gapResult,
  onRequestTeaming,
}: PartnerResultsListProps) {
  return (
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
              <PartnerCard
                key={p.id}
                partner={p}
                gapResult={gapResult}
                onRequestTeaming={onRequestTeaming}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PartnerCard({
  partner: p,
  gapResult,
  onRequestTeaming,
}: {
  partner: TeamingPartnerPublicProfile;
  gapResult: CapabilityGapResult | null;
  onRequestTeaming: (partnerId: number) => void;
}) {
  const gapMatches = gapResult
    ? gapResult.gaps.filter((gap) => gap.matching_partner_ids.includes(p.id))
    : [];
  const recommendedReason = gapResult?.recommended_partners.find(
    (partner) => partner.partner_id === p.id
  )?.reason;
  const hasFitSignal = gapMatches.length > 0 || Boolean(recommendedReason);

  return (
    <div className="border rounded-lg p-4">
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
          onClick={() => onRequestTeaming(p.id)}
        >
          Request Teaming
        </Button>
      </div>
    </div>
  );
}
