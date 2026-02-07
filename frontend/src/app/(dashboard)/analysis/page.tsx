"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileSearch,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate, cn } from "@/lib/utils";
import { rfpApi } from "@/lib/api";
import type { RFPListItem } from "@/types";

interface AnalyzedRFP extends RFPListItem {
  requirements_total: number;
  requirements_addressed: number;
  analyzed_at: string;
}

export default function AnalysisIndexPage() {
  const [analyzedRFPs, setAnalyzedRFPs] = useState<AnalyzedRFP[]>([]);
  const [stats, setStats] = useState({
    total: 0,
    sectionsGenerated: 0,
    pendingReview: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);

        // Fetch analyzed RFPs (status = analyzed or later)
        const rfps = await rfpApi.list({ status: "analyzed" });

        // Transform RFPs to include analysis data
        const analyzed: AnalyzedRFP[] = rfps.map((rfp) => ({
          ...rfp,
          requirements_total: rfp.requirements_count || 0,
          requirements_addressed: rfp.sections_generated || 0,
          analyzed_at: rfp.analyzed_at || rfp.updated_at || rfp.created_at,
        }));

        setAnalyzedRFPs(analyzed);

        // Fetch stats
        const rfpStats = await rfpApi.getStats();
        const totalSections = analyzed.reduce(
          (sum, rfp) => sum + (rfp.requirements_addressed || 0),
          0
        );
        const pendingReview = analyzed.reduce(
          (sum, rfp) =>
            sum + ((rfp.requirements_total || 0) - (rfp.requirements_addressed || 0)),
          0
        );

        setStats({
          total: analyzed.length,
          sectionsGenerated: totalSections,
          pendingReview: pendingReview,
        });
      } catch (err) {
        console.error("Failed to fetch analysis data:", err);
        setError("Failed to load analysis data. Please try again.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <Header
          title="Analysis"
          description="Deep-dive into RFP requirements and generate proposals"
        />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col h-full">
        <Header
          title="Analysis"
          description="Deep-dive into RFP requirements and generate proposals"
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <AlertTriangle className="w-12 h-12 text-destructive mx-auto mb-4" />
            <p className="text-destructive">{error}</p>
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => window.location.reload()}
            >
              Retry
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Analysis"
        description="Deep-dive into RFP requirements and generate proposals"
      />

      <div className="flex-1 p-6 overflow-auto">
        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Analyzed RFPs</p>
                  <p className="text-3xl font-bold text-primary mt-1">
                    {stats.total}
                  </p>
                </div>
                <BarChart3 className="w-10 h-10 text-primary/30" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-accent/5 to-accent/10 border-accent/20">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">
                    Sections Generated
                  </p>
                  <p className="text-3xl font-bold text-accent mt-1">
                    {stats.sectionsGenerated}
                  </p>
                </div>
                <CheckCircle2 className="w-10 h-10 text-accent/30" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-warning/5 to-warning/10 border-warning/20">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Pending Review</p>
                  <p className="text-3xl font-bold text-warning mt-1">
                    {stats.pendingReview}
                  </p>
                </div>
                <Clock className="w-10 h-10 text-warning/30" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Analyzed RFPs */}
        {analyzedRFPs.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold mb-4">Ready for Proposal Writing</h2>

            <div className="grid gap-4">
              {analyzedRFPs.map((rfp) => {
                const progress =
                  rfp.requirements_total > 0
                    ? (rfp.requirements_addressed / rfp.requirements_total) * 100
                    : 0;
                const deadline = rfp.response_deadline;
                const daysLeft = deadline
                  ? Math.ceil(
                      (new Date(deadline).getTime() - Date.now()) /
                        (1000 * 60 * 60 * 24)
                    )
                  : null;

                return (
                  <Card key={rfp.id} className="hover:border-primary/30 transition-colors">
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant="outline" className="text-xs">
                              {rfp.solicitation_number || rfp.notice_id}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {rfp.agency}
                            </span>
                          </div>

                          <h3 className="font-semibold text-lg mb-3">{rfp.title}</h3>

                          <div className="flex items-center gap-6 text-sm">
                            <div className="flex items-center gap-2">
                              <div className="w-24 h-2 bg-secondary rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-accent"
                                  style={{ width: `${progress}%` }}
                                />
                              </div>
                              <span className="text-muted-foreground">
                                {rfp.requirements_addressed}/{rfp.requirements_total}{" "}
                                sections
                              </span>
                            </div>

                            {daysLeft !== null && (
                              <div
                                className={cn(
                                  "flex items-center gap-1",
                                  daysLeft <= 7 ? "text-warning" : "text-muted-foreground"
                                )}
                              >
                                {daysLeft <= 7 && <AlertTriangle className="w-4 h-4" />}
                                <Clock className="w-4 h-4" />
                                {daysLeft > 0 ? `${daysLeft} days left` : "Past due"}
                              </div>
                            )}

                            <span className="text-muted-foreground">
                              Analyzed {formatDate(rfp.analyzed_at)}
                            </span>
                          </div>
                        </div>

                        <Button asChild>
                          <Link href={`/analysis/${rfp.id}`}>
                            Continue
                            <ArrowRight className="w-4 h-4 ml-1" />
                          </Link>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        )}

        {/* Empty State */}
        {analyzedRFPs.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-20 h-20 rounded-full bg-secondary flex items-center justify-center mb-4">
              <FileSearch className="w-10 h-10 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No Analyzed RFPs</h3>
            <p className="text-muted-foreground text-center max-w-md mb-4">
              Analyze an RFP from the Opportunities page to start generating
              proposals with AI assistance.
            </p>
            <Button asChild>
              <Link href="/opportunities">View Opportunities</Link>
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
