"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { budgetIntelApi } from "@/lib/api";
import type { BudgetIntelligence } from "@/types";

interface BudgetIntelSectionProps {
  rfpId: number;
  initialRecords: BudgetIntelligence[];
  onError: (message: string) => void;
}

export function BudgetIntelSection({ rfpId, initialRecords, onError }: BudgetIntelSectionProps) {
  const [budgetRecords, setBudgetRecords] = useState<BudgetIntelligence[]>(initialRecords);
  const [isSavingBudget, setIsSavingBudget] = useState(false);
  const [budgetForm, setBudgetForm] = useState({
    title: "",
    fiscal_year: "",
    amount: "",
    source_url: "",
    notes: "",
  });

  const handleBudgetChange = (field: keyof typeof budgetForm, value: string) => {
    setBudgetForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreateBudget = async () => {
    if (!budgetForm.title.trim()) return;
    try {
      setIsSavingBudget(true);
      const created = await budgetIntelApi.create({
        rfp_id: rfpId,
        title: budgetForm.title.trim(),
        fiscal_year: budgetForm.fiscal_year
          ? Number(budgetForm.fiscal_year)
          : undefined,
        amount: budgetForm.amount ? Number(budgetForm.amount) : undefined,
        source_url: budgetForm.source_url || undefined,
        notes: budgetForm.notes || undefined,
      });
      setBudgetRecords((prev) => [created, ...prev]);
      setBudgetForm({
        title: "",
        fiscal_year: "",
        amount: "",
        source_url: "",
        notes: "",
      });
    } catch (err) {
      console.error("Failed to create budget record", err);
      onError("Failed to create budget record.");
    } finally {
      setIsSavingBudget(false);
    }
  };

  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Budget Intelligence</p>
            <p className="text-xs text-muted-foreground">
              Track funding signals tied to this opportunity.
            </p>
          </div>
          <Button size="sm" onClick={handleCreateBudget} disabled={isSavingBudget}>
            {isSavingBudget ? "Saving..." : "Add Budget"}
          </Button>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Budget title"
            value={budgetForm.title}
            onChange={(e) => handleBudgetChange("title", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Fiscal year"
            value={budgetForm.fiscal_year}
            onChange={(e) => handleBudgetChange("fiscal_year", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Amount"
            value={budgetForm.amount}
            onChange={(e) => handleBudgetChange("amount", e.target.value)}
          />
        </div>

        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Source URL"
          value={budgetForm.source_url}
          onChange={(e) => handleBudgetChange("source_url", e.target.value)}
        />

        <textarea
          className="min-h-[80px] rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Budget notes"
          value={budgetForm.notes}
          onChange={(e) => handleBudgetChange("notes", e.target.value)}
        />

        {budgetRecords.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No budget intel recorded yet.
          </p>
        ) : (
          <div className="space-y-2">
            {budgetRecords.map((record) => (
              <div
                key={record.id}
                className="rounded-md border border-border px-3 py-2 text-sm"
              >
                <p className="font-medium text-foreground">{record.title}</p>
                <p className="text-xs text-muted-foreground">
                  FY {record.fiscal_year || "—"} ·{" "}
                  {record.amount
                    ? `$${record.amount.toLocaleString()}`
                    : "Amount TBD"}
                </p>
                {record.source_url && (
                  <p className="text-xs text-primary break-all">
                    {record.source_url}
                  </p>
                )}
                {record.notes && (
                  <p className="text-xs text-muted-foreground">
                    {record.notes}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
