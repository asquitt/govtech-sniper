"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Check, ChevronLeft, ChevronRight, Rocket, X } from "lucide-react";
import { cn } from "@/lib/utils";
import api from "@/lib/api/client";
import type { OnboardingProgress } from "@/types";

export function OnboardingWizard() {
  const [progress, setProgress] = useState<OnboardingProgress | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [activeStep, setActiveStep] = useState(0);

  const fetchProgress = useCallback(async () => {
    try {
      const { data } = await api.get("/onboarding/progress");
      if (data.is_dismissed) {
        setDismissed(true);
        return;
      }
      setProgress(data);
    } catch {
      // Not available
    }
  }, []);

  useEffect(() => {
    fetchProgress();
  }, [fetchProgress]);

  useEffect(() => {
    if (!progress) return;
    const firstIncomplete = progress.steps.findIndex((step) => !step.completed);
    setActiveStep(firstIncomplete >= 0 ? firstIncomplete : 0);
  }, [progress]);

  const handleDismiss = async () => {
    try {
      await api.post("/onboarding/dismiss");
      setDismissed(true);
    } catch {
      setDismissed(true);
    }
  };

  if (dismissed || !progress || progress.is_complete) return null;

  const pct = Math.round((progress.completed_count / progress.total_steps) * 100);

  const step = progress.steps[activeStep] ?? progress.steps[0];

  const handleMarkComplete = async () => {
    if (!step || step.completed) return;
    try {
      await api.post(`/onboarding/steps/${step.id}/complete`);
      await fetchProgress();
    } catch {
      // no-op
    }
  };

  return (
    <>
      <Card className="border border-primary/30 bg-gradient-to-br from-primary/5 to-accent/5">
        <CardContent className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Rocket className="h-4 w-4 text-primary" />
              <span className="text-sm font-semibold text-foreground">Getting Started</span>
              <span className="text-xs text-muted-foreground">
                {progress.completed_count}/{progress.total_steps} steps
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Button variant="outline" size="sm" onClick={() => setWizardOpen(true)}>
                Guided Setup
              </Button>
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleDismiss}>
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <div className="mb-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{ width: `${pct}%` }}
            />
          </div>

          <div className="space-y-1.5">
            {progress.steps.map((stepItem) => (
              <Link
                key={stepItem.id}
                href={stepItem.href}
                className={cn(
                  "flex items-center gap-2.5 rounded-md p-2 transition-colors",
                  stepItem.completed
                    ? "text-muted-foreground"
                    : "text-foreground hover:bg-primary/10"
                )}
              >
                <div
                  className={cn(
                    "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border",
                    stepItem.completed ? "border-accent bg-accent" : "border-muted-foreground/40"
                  )}
                >
                  {stepItem.completed && <Check className="h-3 w-3 text-white" />}
                </div>
                <div className="min-w-0 flex-1">
                  <p className={cn("text-xs font-medium", stepItem.completed && "line-through")}>
                    {stepItem.title}
                  </p>
                  {!stepItem.completed && (
                    <p className="text-[10px] text-muted-foreground">{stepItem.description}</p>
                  )}
                </div>
                {!stepItem.completed && (
                  <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                )}
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>

      {wizardOpen && step && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="w-full max-w-xl">
            <CardHeader>
              <CardTitle className="text-base">Guided Setup Wizard</CardTitle>
              <p className="text-xs text-muted-foreground">
                Step {activeStep + 1} of {progress.total_steps}
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-md border border-border p-3">
                <p className="text-sm font-semibold">{step.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{step.description}</p>
                {step.completed && (
                  <p className="mt-2 text-xs font-medium text-emerald-600">Completed</p>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  onClick={() => setActiveStep((prev) => Math.max(0, prev - 1))}
                  disabled={activeStep <= 0}
                >
                  <ChevronLeft className="mr-1 h-4 w-4" />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  onClick={() =>
                    setActiveStep((prev) => Math.min(progress.steps.length - 1, prev + 1))
                  }
                  disabled={activeStep >= progress.steps.length - 1}
                >
                  Next
                  <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
                <Button variant="outline" onClick={handleMarkComplete} disabled={step.completed}>
                  Mark Complete
                </Button>
                <Link href={step.href} className="inline-flex">
                  <Button>Open Step</Button>
                </Link>
                <Button variant="ghost" onClick={() => setWizardOpen(false)}>
                  Close
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
