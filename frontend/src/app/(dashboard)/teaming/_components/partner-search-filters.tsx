"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface PartnerSearchFiltersProps {
  query: string;
  naicsFilter: string;
  capabilityFilter: string;
  clearanceFilter: string;
  onQueryChange: (value: string) => void;
  onNaicsChange: (value: string) => void;
  onCapabilityChange: (value: string) => void;
  onClearanceChange: (value: string) => void;
  onSearch: () => void;
}

export function PartnerSearchFilters({
  query,
  naicsFilter,
  capabilityFilter,
  clearanceFilter,
  onQueryChange,
  onNaicsChange,
  onCapabilityChange,
  onClearanceChange,
  onSearch,
}: PartnerSearchFiltersProps) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="grid grid-cols-4 gap-3">
          <input
            className="border rounded-lg px-3 py-2 text-sm bg-background"
            placeholder="Company name..."
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
          />
          <input
            className="border rounded-lg px-3 py-2 text-sm bg-background"
            placeholder="NAICS code"
            value={naicsFilter}
            onChange={(e) => onNaicsChange(e.target.value)}
          />
          <input
            className="border rounded-lg px-3 py-2 text-sm bg-background"
            placeholder="Capability"
            value={capabilityFilter}
            onChange={(e) => onCapabilityChange(e.target.value)}
          />
          <input
            className="border rounded-lg px-3 py-2 text-sm bg-background"
            placeholder="Clearance level"
            value={clearanceFilter}
            onChange={(e) => onClearanceChange(e.target.value)}
          />
        </div>
        <div className="mt-3">
          <Button size="sm" onClick={onSearch}>
            Search
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
