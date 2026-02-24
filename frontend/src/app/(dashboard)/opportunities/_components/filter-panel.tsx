"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export interface FilterPanelProps {
  sourceTypeFilter: string;
  jurisdictionFilter: string;
  currencyFilter: string;
  onSourceTypeChange: (value: string) => void;
  onJurisdictionChange: (value: string) => void;
  onCurrencyChange: (value: string) => void;
  onClear: () => void;
}

export function FilterPanel({
  sourceTypeFilter,
  jurisdictionFilter,
  currencyFilter,
  onSourceTypeChange,
  onJurisdictionChange,
  onCurrencyChange,
  onClear,
}: FilterPanelProps) {
  return (
    <Card className="mb-4 border border-border">
      <CardContent className="p-3 grid grid-cols-1 md:grid-cols-4 gap-3">
        <label className="text-xs text-muted-foreground">
          Source Type
          <select
            className="mt-1 h-9 w-full rounded-md border border-border bg-background px-2 text-sm text-foreground"
            value={sourceTypeFilter}
            onChange={(event) => onSourceTypeChange(event.target.value)}
          >
            <option value="">Any Source</option>
            <option value="federal">Federal</option>
            <option value="sled">SLED</option>
            <option value="canada_buyandsell">Canada Buy & Sell</option>
            <option value="canada_provincial">Canada Provincial</option>
            <option value="fpds">FPDS</option>
            <option value="email">Email</option>
          </select>
        </label>

        <label className="text-xs text-muted-foreground">
          Jurisdiction
          <select
            className="mt-1 h-9 w-full rounded-md border border-border bg-background px-2 text-sm text-foreground"
            value={jurisdictionFilter}
            onChange={(event) => onJurisdictionChange(event.target.value)}
          >
            <option value="">Any Jurisdiction</option>
            <option value="US">United States</option>
            <option value="CA">Canada</option>
            <option value="CA-AB">Canada - Alberta</option>
            <option value="CA-BC">Canada - British Columbia</option>
            <option value="CA-MB">Canada - Manitoba</option>
            <option value="CA-NB">Canada - New Brunswick</option>
            <option value="CA-NL">Canada - Newfoundland and Labrador</option>
            <option value="CA-NS">Canada - Nova Scotia</option>
            <option value="CA-NT">Canada - Northwest Territories</option>
            <option value="CA-NU">Canada - Nunavut</option>
            <option value="CA-ON">Canada - Ontario</option>
            <option value="CA-PE">Canada - Prince Edward Island</option>
            <option value="CA-QC">Canada - Quebec</option>
            <option value="CA-SK">Canada - Saskatchewan</option>
            <option value="CA-YT">Canada - Yukon</option>
          </select>
        </label>

        <label className="text-xs text-muted-foreground">
          Currency
          <select
            className="mt-1 h-9 w-full rounded-md border border-border bg-background px-2 text-sm text-foreground"
            value={currencyFilter}
            onChange={(event) => onCurrencyChange(event.target.value)}
          >
            <option value="">Any Currency</option>
            <option value="USD">USD</option>
            <option value="CAD">CAD</option>
          </select>
        </label>

        <div className="flex items-end">
          <Button variant="outline" className="w-full" onClick={onClear}>
            Clear Filters
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
