"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";

export interface BillingToggleProps {
  annual: boolean;
  onToggle: (value: boolean) => void;
}

export function BillingToggle({ annual, onToggle }: BillingToggleProps) {
  return (
    <div className="flex items-center justify-center gap-3">
      <span
        className={`text-sm cursor-pointer ${!annual ? "font-semibold text-foreground" : "text-muted-foreground"}`}
        onClick={() => onToggle(false)}
      >
        Monthly
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={annual}
        onClick={() => onToggle(!annual)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          annual ? "bg-primary" : "bg-muted"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
            annual ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
      <span
        className={`text-sm cursor-pointer ${annual ? "font-semibold text-foreground" : "text-muted-foreground"}`}
        onClick={() => onToggle(true)}
      >
        Annual
        <Badge variant="success" className="ml-1.5 text-[10px]">
          Save 20%
        </Badge>
      </span>
    </div>
  );
}
