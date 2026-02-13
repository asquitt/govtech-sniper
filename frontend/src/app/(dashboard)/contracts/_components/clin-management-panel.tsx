"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { contractApi } from "@/lib/api";
import type { ContractCLIN } from "@/types";

interface CLINManagementPanelProps {
  selectedContractId: number | null;
  clins: ContractCLIN[];
  onClinsChange: (clins: ContractCLIN[]) => void;
  onError: (msg: string) => void;
}

export function CLINManagementPanel({
  selectedContractId,
  clins,
  onClinsChange,
  onError,
}: CLINManagementPanelProps) {
  const [clinNumber, setClinNumber] = useState("");
  const [clinDescription, setClinDescription] = useState("");
  const [clinType, setClinType] = useState("");
  const [clinQuantity, setClinQuantity] = useState("");
  const [clinUnitPrice, setClinUnitPrice] = useState("");
  const [clinFundedAmount, setClinFundedAmount] = useState("");
  const [clinEditingId, setClinEditingId] = useState<number | null>(null);
  const [editingQuantity, setEditingQuantity] = useState("");
  const [editingFundedAmount, setEditingFundedAmount] = useState("");

  const handleCreateCLIN = async () => {
    if (!selectedContractId || !clinNumber.trim()) return;
    const quantity = clinQuantity ? Number.parseInt(clinQuantity, 10) : undefined;
    const unitPrice = clinUnitPrice ? Number.parseFloat(clinUnitPrice) : undefined;
    const fundedAmount = clinFundedAmount
      ? Number.parseFloat(clinFundedAmount)
      : undefined;
    const totalValue =
      quantity !== undefined && unitPrice !== undefined
        ? quantity * unitPrice
        : undefined;

    try {
      await contractApi.createCLIN(selectedContractId, {
        clin_number: clinNumber.trim(),
        description: clinDescription.trim() || undefined,
        clin_type: clinType.trim() || undefined,
        quantity,
        unit_price: unitPrice,
        funded_amount: fundedAmount,
        total_value: totalValue,
      });
      setClinNumber("");
      setClinDescription("");
      setClinType("");
      setClinQuantity("");
      setClinUnitPrice("");
      setClinFundedAmount("");
      const clinList = await contractApi.listCLINs(selectedContractId);
      onClinsChange(clinList);
    } catch (err) {
      console.error("Failed to create CLIN", err);
      onError("Failed to create CLIN.");
    }
  };

  const handleSaveCLIN = async (clinId: number) => {
    if (!selectedContractId) return;
    const quantity = editingQuantity ? Number.parseInt(editingQuantity, 10) : undefined;
    const fundedAmount = editingFundedAmount
      ? Number.parseFloat(editingFundedAmount)
      : undefined;
    const target = clins.find((item) => item.id === clinId);
    const unitPrice = target?.unit_price ?? undefined;
    const totalValue =
      quantity !== undefined && unitPrice !== undefined
        ? quantity * unitPrice
        : target?.total_value ?? undefined;

    try {
      await contractApi.updateCLIN(selectedContractId, clinId, {
        quantity,
        funded_amount: fundedAmount,
        total_value: totalValue,
      });
      const clinList = await contractApi.listCLINs(selectedContractId);
      onClinsChange(clinList);
      setClinEditingId(null);
      setEditingQuantity("");
      setEditingFundedAmount("");
    } catch (err) {
      console.error("Failed to update CLIN", err);
      onError("Failed to update CLIN.");
    }
  };

  const handleDeleteCLIN = async (clinId: number) => {
    if (!selectedContractId) return;
    try {
      await contractApi.deleteCLIN(selectedContractId, clinId);
      const clinList = await contractApi.listCLINs(selectedContractId);
      onClinsChange(clinList);
    } catch (err) {
      console.error("Failed to delete CLIN", err);
      onError("Failed to delete CLIN.");
    }
  };

  return (
    <div className="mt-6 space-y-3">
      <p className="text-sm font-medium">CLIN Management</p>
      <div className="grid grid-cols-6 gap-2">
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="CLIN #"
          value={clinNumber}
          onChange={(e) => setClinNumber(e.target.value)}
        />
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="CLIN description"
          value={clinDescription}
          onChange={(e) => setClinDescription(e.target.value)}
        />
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="CLIN type"
          value={clinType}
          onChange={(e) => setClinType(e.target.value)}
        />
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          type="number"
          placeholder="Qty"
          value={clinQuantity}
          onChange={(e) => setClinQuantity(e.target.value)}
        />
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          type="number"
          step="0.01"
          placeholder="Unit price"
          value={clinUnitPrice}
          onChange={(e) => setClinUnitPrice(e.target.value)}
        />
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          type="number"
          step="0.01"
          placeholder="Funded"
          value={clinFundedAmount}
          onChange={(e) => setClinFundedAmount(e.target.value)}
        />
      </div>
      <Button onClick={handleCreateCLIN}>Add CLIN</Button>
      <div className="space-y-2">
        {clins.length === 0 ? (
          <p className="text-sm text-muted-foreground">No CLINs yet.</p>
        ) : (
          clins.map((clin) => (
            <div
              key={clin.id}
              className="rounded-md border border-border px-3 py-2 text-sm space-y-2"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{clin.clin_number}</p>
                  <p className="text-xs text-muted-foreground">
                    {clin.description || "No description"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{clin.clin_type || "type n/a"}</Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteCLIN(clin.id)}
                  >
                    Remove
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-4 gap-2 text-xs text-muted-foreground">
                <span>Qty: {clin.quantity ?? "n/a"}</span>
                <span>
                  Unit:{" "}
                  {clin.unit_price != null
                    ? clin.unit_price.toLocaleString(undefined, {
                        style: "currency",
                        currency: "USD",
                        maximumFractionDigits: 0,
                      })
                    : "n/a"}
                </span>
                <span>
                  Total:{" "}
                  {clin.total_value != null
                    ? clin.total_value.toLocaleString(undefined, {
                        style: "currency",
                        currency: "USD",
                        maximumFractionDigits: 0,
                      })
                    : "n/a"}
                </span>
                <span>
                  Funded:{" "}
                  {clin.funded_amount != null
                    ? clin.funded_amount.toLocaleString(undefined, {
                        style: "currency",
                        currency: "USD",
                        maximumFractionDigits: 0,
                      })
                    : "n/a"}
                </span>
              </div>
              {clinEditingId === clin.id ? (
                <div className="flex items-center gap-2">
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-xs"
                    type="number"
                    placeholder="Qty"
                    value={editingQuantity}
                    onChange={(e) => setEditingQuantity(e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-xs"
                    type="number"
                    step="0.01"
                    placeholder="Funded amount"
                    value={editingFundedAmount}
                    onChange={(e) => setEditingFundedAmount(e.target.value)}
                  />
                  <Button size="sm" onClick={() => handleSaveCLIN(clin.id)}>
                    Save
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setClinEditingId(null);
                      setEditingQuantity("");
                      setEditingFundedAmount("");
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setClinEditingId(clin.id);
                    setEditingQuantity(
                      clin.quantity != null ? String(clin.quantity) : ""
                    );
                    setEditingFundedAmount(
                      clin.funded_amount != null ? String(clin.funded_amount) : ""
                    );
                  }}
                >
                  Edit Quantity/Funded
                </Button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
