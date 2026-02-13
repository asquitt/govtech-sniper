"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { contractApi } from "@/lib/api";
import type { ContractAward, ContractStatus, ContractType } from "@/types";

const statusOptions: { value: ContractStatus; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "at_risk", label: "At Risk" },
  { value: "completed", label: "Completed" },
  { value: "on_hold", label: "On Hold" },
];

interface ContractCreationFormProps {
  contracts: ContractAward[];
  onCreated: () => Promise<void>;
  onError: (msg: string) => void;
}

export function ContractCreationForm({
  contracts,
  onCreated,
  onError,
}: ContractCreationFormProps) {
  const [title, setTitle] = useState("");
  const [number, setNumber] = useState("");
  const [agency, setAgency] = useState("");
  const [contractType, setContractType] = useState<ContractType>("prime");
  const [parentContractId, setParentContractId] = useState("");
  const [status, setStatus] = useState<ContractStatus>("active");

  const handleCreateContract = async () => {
    if (!title.trim() || !number.trim()) return;
    try {
      await contractApi.create({
        contract_number: number.trim(),
        title: title.trim(),
        agency: agency.trim() || undefined,
        parent_contract_id: parentContractId
          ? Number.parseInt(parentContractId, 10)
          : undefined,
        contract_type: contractType,
        status,
      });
      setTitle("");
      setNumber("");
      setAgency("");
      setContractType("prime");
      setParentContractId("");
      await onCreated();
    } catch (err) {
      console.error("Failed to create contract", err);
      onError("Failed to create contract.");
    }
  };

  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-3">
        <p className="text-sm font-medium">New Contract</p>
        <div className="grid grid-cols-6 gap-3">
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Contract #"
            value={number}
            onChange={(e) => setNumber(e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Agency"
            value={agency}
            onChange={(e) => setAgency(e.target.value)}
          />
          <select
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            aria-label="Contract status"
            value={status}
            onChange={(e) => setStatus(e.target.value as ContractStatus)}
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            aria-label="Contract type"
            value={contractType}
            onChange={(e) => setContractType(e.target.value as ContractType)}
          >
            <option value="prime">Prime</option>
            <option value="subcontract">Subcontract</option>
            <option value="idiq">IDIQ</option>
            <option value="task_order">Task Order</option>
            <option value="bpa">BPA</option>
          </select>
          <select
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            aria-label="Parent contract"
            value={parentContractId}
            onChange={(e) => setParentContractId(e.target.value)}
          >
            <option value="">Top-level contract</option>
            {contracts.map((contract) => (
              <option key={contract.id} value={contract.id}>
                {contract.contract_number}
              </option>
            ))}
          </select>
        </div>
        <Button onClick={handleCreateContract}>Create Contract</Button>
      </CardContent>
    </Card>
  );
}
