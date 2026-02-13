"use client";

import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { rfpApi } from "@/lib/api";
import type { RFP } from "@/types";

interface MarketIntelFormProps {
  rfp: RFP;
  onUpdate: (updated: RFP) => void;
  onError: (message: string) => void;
}

export function MarketIntelForm({ rfp, onUpdate, onError }: MarketIntelFormProps) {
  const [isSavingIntel, setIsSavingIntel] = useState(false);
  const [intelForm, setIntelForm] = useState({
    source_type: "",
    jurisdiction: "",
    contract_vehicle: "",
    incumbent_vendor: "",
    buyer_contact_name: "",
    buyer_contact_email: "",
    buyer_contact_phone: "",
    budget_estimate: "",
    competitive_landscape: "",
    intel_notes: "",
  });

  useEffect(() => {
    setIntelForm({
      source_type: rfp.source_type || "",
      jurisdiction: rfp.jurisdiction || "",
      contract_vehicle: rfp.contract_vehicle || "",
      incumbent_vendor: rfp.incumbent_vendor || "",
      buyer_contact_name: rfp.buyer_contact_name || "",
      buyer_contact_email: rfp.buyer_contact_email || "",
      buyer_contact_phone: rfp.buyer_contact_phone || "",
      budget_estimate: rfp.budget_estimate ? String(rfp.budget_estimate) : "",
      competitive_landscape: rfp.competitive_landscape || "",
      intel_notes: rfp.intel_notes || "",
    });
  }, [rfp]);

  const handleIntelChange = (field: keyof typeof intelForm, value: string) => {
    setIntelForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveIntel = async () => {
    try {
      setIsSavingIntel(true);
      const payload: Partial<RFP> = {
        source_type: intelForm.source_type || undefined,
        jurisdiction: intelForm.jurisdiction || undefined,
        contract_vehicle: intelForm.contract_vehicle || undefined,
        incumbent_vendor: intelForm.incumbent_vendor || undefined,
        buyer_contact_name: intelForm.buyer_contact_name || undefined,
        buyer_contact_email: intelForm.buyer_contact_email || undefined,
        buyer_contact_phone: intelForm.buyer_contact_phone || undefined,
        budget_estimate: intelForm.budget_estimate
          ? Number(intelForm.budget_estimate)
          : undefined,
        competitive_landscape: intelForm.competitive_landscape || undefined,
        intel_notes: intelForm.intel_notes || undefined,
      };
      const updated = await rfpApi.update(rfp.id, payload);
      onUpdate(updated);
    } catch (saveErr) {
      console.error("Failed to save market intelligence", saveErr);
      onError("Failed to save market intelligence.");
    } finally {
      setIsSavingIntel(false);
    }
  };

  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Market Intelligence</p>
            <p className="text-xs text-muted-foreground">
              Track vehicles, incumbents, buyer contacts, and competitive context.
            </p>
          </div>
          <Button size="sm" onClick={handleSaveIntel} disabled={isSavingIntel}>
            {isSavingIntel ? "Saving..." : "Save Intel"}
          </Button>
        </div>

        <div className="grid gap-3 md:grid-cols-3 text-sm">
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Source Type (federal, sled)"
            value={intelForm.source_type}
            onChange={(e) => handleIntelChange("source_type", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Jurisdiction (e.g., VA)"
            value={intelForm.jurisdiction}
            onChange={(e) => handleIntelChange("jurisdiction", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Contract Vehicle"
            value={intelForm.contract_vehicle}
            onChange={(e) => handleIntelChange("contract_vehicle", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Incumbent Vendor"
            value={intelForm.incumbent_vendor}
            onChange={(e) => handleIntelChange("incumbent_vendor", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Budget Estimate"
            value={intelForm.budget_estimate}
            onChange={(e) => handleIntelChange("budget_estimate", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Buyer Contact Name"
            value={intelForm.buyer_contact_name}
            onChange={(e) => handleIntelChange("buyer_contact_name", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Buyer Contact Email"
            value={intelForm.buyer_contact_email}
            onChange={(e) => handleIntelChange("buyer_contact_email", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Buyer Contact Phone"
            value={intelForm.buyer_contact_phone}
            onChange={(e) => handleIntelChange("buyer_contact_phone", e.target.value)}
          />
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <textarea
            className="min-h-[100px] rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Competitive landscape notes"
            value={intelForm.competitive_landscape}
            onChange={(e) =>
              handleIntelChange("competitive_landscape", e.target.value)
            }
          />
          <textarea
            className="min-h-[100px] rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Additional intel notes"
            value={intelForm.intel_notes}
            onChange={(e) => handleIntelChange("intel_notes", e.target.value)}
          />
        </div>
      </CardContent>
    </Card>
  );
}
