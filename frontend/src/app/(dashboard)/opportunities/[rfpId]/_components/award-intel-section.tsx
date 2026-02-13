"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { awardApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { AwardRecord } from "@/types";

interface AwardIntelSectionProps {
  rfpId: number;
  initialAwards: AwardRecord[];
  onError: (message: string) => void;
}

export function AwardIntelSection({ rfpId, initialAwards, onError }: AwardIntelSectionProps) {
  const [awards, setAwards] = useState<AwardRecord[]>(initialAwards);
  const [isSavingAward, setIsSavingAward] = useState(false);
  const [awardForm, setAwardForm] = useState({
    awardee_name: "",
    award_amount: "",
    award_date: "",
    contract_vehicle: "",
    contract_number: "",
    description: "",
    source_url: "",
  });

  const handleAwardChange = (field: keyof typeof awardForm, value: string) => {
    setAwardForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreateAward = async () => {
    if (!awardForm.awardee_name.trim()) return;
    try {
      setIsSavingAward(true);
      const payload = {
        rfp_id: rfpId,
        awardee_name: awardForm.awardee_name.trim(),
        award_amount: awardForm.award_amount
          ? Number(awardForm.award_amount)
          : undefined,
        award_date: awardForm.award_date || undefined,
        contract_vehicle: awardForm.contract_vehicle || undefined,
        contract_number: awardForm.contract_number || undefined,
        description: awardForm.description || undefined,
        source_url: awardForm.source_url || undefined,
      };
      const created = await awardApi.create(payload);
      setAwards((prev) => [created, ...prev]);
      setAwardForm({
        awardee_name: "",
        award_amount: "",
        award_date: "",
        contract_vehicle: "",
        contract_number: "",
        description: "",
        source_url: "",
      });
    } catch (err) {
      console.error("Failed to create award record", err);
      onError("Failed to create award record.");
    } finally {
      setIsSavingAward(false);
    }
  };

  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Award Intelligence</p>
            <p className="text-xs text-muted-foreground">
              Track awardees, values, and vehicles tied to this opportunity.
            </p>
          </div>
          <Button size="sm" onClick={handleCreateAward} disabled={isSavingAward}>
            {isSavingAward ? "Saving..." : "Add Award"}
          </Button>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Awardee Name"
            value={awardForm.awardee_name}
            onChange={(e) => handleAwardChange("awardee_name", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Award Amount"
            value={awardForm.award_amount}
            onChange={(e) => handleAwardChange("award_amount", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Award Date (YYYY-MM-DD)"
            value={awardForm.award_date}
            onChange={(e) => handleAwardChange("award_date", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Contract Vehicle"
            value={awardForm.contract_vehicle}
            onChange={(e) => handleAwardChange("contract_vehicle", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Contract Number"
            value={awardForm.contract_number}
            onChange={(e) => handleAwardChange("contract_number", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Source URL"
            value={awardForm.source_url}
            onChange={(e) => handleAwardChange("source_url", e.target.value)}
          />
        </div>

        <textarea
          className="min-h-[80px] rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Award description or notes"
          value={awardForm.description}
          onChange={(e) => handleAwardChange("description", e.target.value)}
        />

        {awards.length === 0 ? (
          <p className="text-sm text-muted-foreground">No awards recorded yet.</p>
        ) : (
          <div className="space-y-2">
            {awards.map((award) => (
              <div
                key={award.id}
                className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
              >
                <div>
                  <p className="font-medium text-foreground">
                    {award.awardee_name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {award.award_amount
                      ? `$${award.award_amount.toLocaleString()}`
                      : "—"}{" "}
                    · {award.contract_vehicle || "Vehicle unknown"}
                  </p>
                </div>
                <Badge variant="outline">
                  {award.award_date ? formatDate(award.award_date) : "Date TBD"}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
