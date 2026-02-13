"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { contractApi } from "@/lib/api";
import type { ContractModification } from "@/types";

interface ModificationsPanelProps {
  selectedContractId: number | null;
  modifications: ContractModification[];
  onModificationsChange: (mods: ContractModification[]) => void;
  onError: (msg: string) => void;
}

export function ModificationsPanel({
  selectedContractId,
  modifications,
  onModificationsChange,
  onError,
}: ModificationsPanelProps) {
  const [modNumber, setModNumber] = useState("");
  const [modType, setModType] = useState("");
  const [modDescription, setModDescription] = useState("");
  const [modEffectiveDate, setModEffectiveDate] = useState("");
  const [modValueChange, setModValueChange] = useState("");

  const handleCreateModification = async () => {
    if (!selectedContractId || !modNumber.trim()) return;
    try {
      await contractApi.createModification(selectedContractId, {
        modification_number: modNumber.trim(),
        mod_type: modType.trim() || undefined,
        description: modDescription.trim() || undefined,
        effective_date: modEffectiveDate || undefined,
        value_change: modValueChange ? Number.parseFloat(modValueChange) : undefined,
      });
      setModNumber("");
      setModType("");
      setModDescription("");
      setModEffectiveDate("");
      setModValueChange("");
      const modList = await contractApi.listModifications(selectedContractId);
      onModificationsChange(modList);
    } catch (err) {
      console.error("Failed to create modification", err);
      onError("Failed to create modification.");
    }
  };

  const handleDeleteModification = async (modId: number) => {
    if (!selectedContractId) return;
    try {
      await contractApi.deleteModification(selectedContractId, modId);
      const modList = await contractApi.listModifications(selectedContractId);
      onModificationsChange(modList);
    } catch (err) {
      console.error("Failed to delete modification", err);
      onError("Failed to delete modification.");
    }
  };

  return (
    <div className="mt-6 space-y-3">
      <p className="text-sm font-medium">Contract Modifications</p>
      <div className="grid grid-cols-5 gap-2">
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Mod #"
          value={modNumber}
          onChange={(e) => setModNumber(e.target.value)}
        />
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Modification type"
          value={modType}
          onChange={(e) => setModType(e.target.value)}
        />
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          aria-label="Modification effective date"
          type="date"
          value={modEffectiveDate}
          onChange={(e) => setModEffectiveDate(e.target.value)}
        />
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          type="number"
          step="0.01"
          placeholder="Value change"
          value={modValueChange}
          onChange={(e) => setModValueChange(e.target.value)}
        />
        <Button onClick={handleCreateModification}>Add Mod</Button>
      </div>
      <input
        className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
        placeholder="Modification description"
        value={modDescription}
        onChange={(e) => setModDescription(e.target.value)}
      />
      <div className="space-y-2">
        {modifications.length === 0 ? (
          <p className="text-sm text-muted-foreground">No modifications yet.</p>
        ) : (
          modifications.map((mod) => (
            <div
              key={mod.id}
              className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
            >
              <div>
                <p className="font-medium">{mod.modification_number}</p>
                <p className="text-xs text-muted-foreground">
                  {[mod.mod_type || "type n/a", mod.effective_date || "date n/a"]
                    .filter(Boolean)
                    .join(" • ")}
                </p>
                {mod.description && (
                  <p className="text-xs text-muted-foreground">{mod.description}</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {mod.value_change != null && (
                  <Badge variant="outline">
                    {mod.value_change >= 0 ? "+" : ""}
                    {mod.value_change.toLocaleString(undefined, {
                      style: "currency",
                      currency: "USD",
                      maximumFractionDigits: 0,
                    })}
                  </Badge>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDeleteModification(mod.id)}
                >
                  Remove
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
