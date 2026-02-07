"use client";

import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertTriangle, Sparkles, Users } from "lucide-react";
import type { CapabilityGapResult } from "@/types";
import { teamingBoardApi } from "@/lib/api/teaming";

interface CapabilityGapCardProps {
  rfpId: number;
  onRequestTeaming?: (partnerId: number) => void;
}

const GAP_ICONS: Record<string, string> = {
  technical: "🔧",
  clearance: "🔒",
  naics: "📋",
  past_performance: "📊",
  set_aside: "🏷️",
};

export function CapabilityGapCard({ rfpId, onRequestTeaming }: CapabilityGapCardProps) {
  const [result, setResult] = useState<CapabilityGapResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await teamingBoardApi.getGapAnalysis(rfpId);
      setResult(data);
    } catch (err) {
      setError("Failed to run gap analysis");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Don't auto-analyze — let user trigger it
  }, [rfpId]);

  if (!result && !loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Sparkles className="w-4 h-4 text-primary" />
            AI Capability Gap Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-3">
            Analyze this RFP to identify capability gaps and recommended teaming partners.
          </p>
          <Button onClick={analyze} disabled={loading} size="sm">
            <Sparkles className="w-3.5 h-3.5 mr-1" />
            Run Analysis
          </Button>
          {error && <p className="text-sm text-destructive mt-2">{error}</p>}
        </CardContent>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground animate-pulse">
            Running AI gap analysis...
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!result) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Sparkles className="w-4 h-4 text-primary" />
          Capability Gap Analysis
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary */}
        <p className="text-sm">{result.analysis_summary}</p>

        {/* Gaps */}
        {result.gaps.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              Identified Gaps ({result.gaps.length})
            </h4>
            <div className="space-y-2">
              {result.gaps.map((gap, i) => (
                <div key={i} className="rounded-lg border border-border p-2.5 space-y-1">
                  <div className="flex items-center gap-1.5">
                    <span>{GAP_ICONS[gap.gap_type] ?? "❓"}</span>
                    <Badge variant="secondary" className="text-xs capitalize">
                      {gap.gap_type.replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <p className="text-sm">{gap.description}</p>
                  {gap.required_value && (
                    <p className="text-xs text-muted-foreground">
                      Required: {gap.required_value}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommended Partners */}
        {result.recommended_partners.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
              <Users className="w-3.5 h-3.5" />
              Recommended Partners
            </h4>
            <div className="space-y-1.5">
              {result.recommended_partners.map((partner) => (
                <div
                  key={partner.partner_id}
                  className="flex items-center justify-between rounded-lg border border-border p-2"
                >
                  <div>
                    <p className="text-sm font-medium">{partner.name}</p>
                    <p className="text-xs text-muted-foreground">{partner.reason}</p>
                  </div>
                  {onRequestTeaming && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onRequestTeaming(partner.partner_id)}
                    >
                      Request
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <Button variant="ghost" size="sm" onClick={analyze} className="text-xs">
          Re-run Analysis
        </Button>
      </CardContent>
    </Card>
  );
}
