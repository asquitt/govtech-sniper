"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Check, ChevronRight, Rocket, X } from "lucide-react";
import { cn } from "@/lib/utils";
import api from "@/lib/api/client";
import type { OnboardingProgress } from "@/types";

export function OnboardingWizard() {
  const [progress, setProgress] = useState<OnboardingProgress | null>(null);
  const [dismissed, setDismissed] = useState(false);

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

  return (
    <Card className="border border-primary/30 bg-gradient-to-br from-primary/5 to-accent/5">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Rocket className="h-4 w-4 text-primary" />
            <span className="text-sm font-semibold text-foreground">
              Getting Started
            </span>
            <span className="text-xs text-muted-foreground">
              {progress.completed_count}/{progress.total_steps} steps
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={handleDismiss}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>

        {/* Progress bar */}
        <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden mb-3">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Steps */}
        <div className="space-y-1.5">
          {progress.steps.map((step) => (
            <Link
              key={step.id}
              href={step.href}
              className={cn(
                "flex items-center gap-2.5 p-2 rounded-md transition-colors",
                step.completed
                  ? "text-muted-foreground"
                  : "text-foreground hover:bg-primary/10"
              )}
            >
              <div
                className={cn(
                  "w-5 h-5 rounded-full flex items-center justify-center shrink-0 border",
                  step.completed
                    ? "bg-accent border-accent"
                    : "border-muted-foreground/40"
                )}
              >
                {step.completed && <Check className="h-3 w-3 text-white" />}
              </div>
              <div className="flex-1 min-w-0">
                <p
                  className={cn(
                    "text-xs font-medium",
                    step.completed && "line-through"
                  )}
                >
                  {step.title}
                </p>
                {!step.completed && (
                  <p className="text-[10px] text-muted-foreground">
                    {step.description}
                  </p>
                )}
              </div>
              {!step.completed && (
                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              )}
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
