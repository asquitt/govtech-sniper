"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const FREE_FEATURES = [
  "SAM.gov opportunity tracking (30-day focus)",
  "Saved searches and filtering",
  "Basic AI opportunity qualification",
  "Up to 10 tracked opportunities",
  "Up to 5 proposal workspaces",
];

const UPGRADE_FEATURES = [
  "Unlimited proposals and higher API quotas",
  "Deep Read and advanced AI drafting",
  "Word add-in and compliance workflows",
  "Cross-org collaboration and enterprise controls",
];

export default function FreeTierPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-14">
        <header className="space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
            <Target className="h-3.5 w-3.5" />
            Free Tier
          </div>
          <h1 className="text-3xl font-bold text-foreground">
            Start winning contracts with zero upfront cost
          </h1>
          <p className="max-w-3xl text-sm text-muted-foreground">
            RFP Sniper&apos;s free tier is built for immediate value: discover opportunities,
            qualify them with AI, and stand up proposal workspaces before upgrading.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button asChild>
              <Link href="/register">
                Create Free Account
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/settings/subscription">View Full Plans</Link>
            </Button>
          </div>
        </header>

        <div className="grid gap-4 md:grid-cols-2">
          <Card className="border-primary/30">
            <CardHeader>
              <CardTitle className="text-lg">Included at No Cost</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {FREE_FEATURES.map((item) => (
                <div key={item} className="flex items-start gap-2 text-sm">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 text-accent" />
                  <span className="text-foreground">{item}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">When You Are Ready to Upgrade</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {UPGRADE_FEATURES.map((item) => (
                <div key={item} className="flex items-start gap-2 text-sm">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 text-primary" />
                  <span className="text-foreground">{item}</span>
                </div>
              ))}
              <p className="pt-1 text-xs text-muted-foreground">
                In-product nudges notify you before limits block your workflow.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
