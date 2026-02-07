"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { X, ChevronRight } from "lucide-react";

const TOUR_STORAGE_KEY = "feature_tour_complete";

interface TourStop {
  target: string;
  title: string;
  description: string;
  position: "right" | "bottom";
}

const TOUR_STOPS: TourStop[] = [
  {
    target: '[href="/opportunities"]',
    title: "Opportunities",
    description: "Browse and ingest government solicitations from SAM.gov.",
    position: "right",
  },
  {
    target: '[href="/analysis"]',
    title: "AI Analysis",
    description:
      "Get instant AI-powered qualification screening and compliance analysis.",
    position: "right",
  },
  {
    target: '[href="/proposals"]',
    title: "Proposal Editor",
    description:
      "Draft winning proposals with AI assistance and citation tracking.",
    position: "right",
  },
  {
    target: '[href="/capture"]',
    title: "Capture Management",
    description: "Track your pipeline stages, bid decisions, and teaming partners.",
    position: "right",
  },
  {
    target: '[href="/settings"]',
    title: "Settings",
    description:
      "Configure integrations, notifications, and team preferences.",
    position: "right",
  },
];

export function FeatureTour() {
  const [currentStop, setCurrentStop] = useState<number | null>(null);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  useEffect(() => {
    const done = localStorage.getItem(TOUR_STORAGE_KEY);
    if (!done) {
      setCurrentStop(0);
    }
  }, []);

  const updatePosition = useCallback(() => {
    if (currentStop === null) return;
    const stop = TOUR_STOPS[currentStop];
    const el = document.querySelector(stop.target);
    if (!el) return;
    const rect = el.getBoundingClientRect();
    if (stop.position === "right") {
      setPosition({ top: rect.top, left: rect.right + 12 });
    } else {
      setPosition({ top: rect.bottom + 12, left: rect.left });
    }
  }, [currentStop]);

  useEffect(() => {
    updatePosition();
    window.addEventListener("resize", updatePosition);
    return () => window.removeEventListener("resize", updatePosition);
  }, [updatePosition]);

  const dismiss = () => {
    localStorage.setItem(TOUR_STORAGE_KEY, "true");
    setCurrentStop(null);
  };

  const next = () => {
    if (currentStop !== null && currentStop < TOUR_STOPS.length - 1) {
      setCurrentStop(currentStop + 1);
    } else {
      dismiss();
    }
  };

  if (currentStop === null) return null;

  const stop = TOUR_STOPS[currentStop];

  return (
    <div className="fixed z-[60] pointer-events-none inset-0">
      <div
        className="absolute pointer-events-auto"
        style={{ top: position.top, left: position.left }}
      >
        <div className="bg-card border border-border rounded-lg shadow-lg p-4 w-64">
          <div className="flex items-start justify-between mb-2">
            <h4 className="font-medium text-foreground text-sm">
              {stop.title}
            </h4>
            <button
              onClick={dismiss}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-muted-foreground mb-3">
            {stop.description}
          </p>
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {currentStop + 1} / {TOUR_STOPS.length}
            </span>
            <Button size="sm" onClick={next} className="h-7 text-xs">
              {currentStop < TOUR_STOPS.length - 1 ? (
                <>
                  Next <ChevronRight className="w-3 h-3 ml-1" />
                </>
              ) : (
                "Finish"
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
