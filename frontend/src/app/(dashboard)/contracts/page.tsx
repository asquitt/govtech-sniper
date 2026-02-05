"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { contractApi } from "@/lib/api";
import type {
  ContractAward,
  ContractDeliverable,
  ContractStatus,
  ContractTask,
  CPARSReview,
} from "@/types";

const statusOptions: { value: ContractStatus; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "at_risk", label: "At Risk" },
  { value: "completed", label: "Completed" },
  { value: "on_hold", label: "On Hold" },
];

export default function ContractsPage() {
  const [contracts, setContracts] = useState<ContractAward[]>([]);
  const [deliverables, setDeliverables] = useState<ContractDeliverable[]>([]);
  const [tasks, setTasks] = useState<ContractTask[]>([]);
  const [cpars, setCpars] = useState<CPARSReview[]>([]);
  const [selectedContractId, setSelectedContractId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [number, setNumber] = useState("");
  const [agency, setAgency] = useState("");
  const [status, setStatus] = useState<ContractStatus>("active");
  const [deliverableTitle, setDeliverableTitle] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [cparsRating, setCparsRating] = useState("");
  const [cparsNotes, setCparsNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const fetchContracts = useCallback(async () => {
    try {
      const { contracts: list } = await contractApi.list();
      setContracts(list);
      if (!selectedContractId && list.length > 0) {
        setSelectedContractId(list[0].id);
      }
    } catch (err) {
      console.error("Failed to load contracts", err);
      setError("Failed to load contracts.");
    }
  }, [selectedContractId]);

  useEffect(() => {
    fetchContracts();
  }, [fetchContracts]);

  useEffect(() => {
    const fetchDeliverables = async () => {
      if (!selectedContractId) return;
      try {
        const list = await contractApi.listDeliverables(selectedContractId);
        setDeliverables(list);
        const taskList = await contractApi.listTasks(selectedContractId);
        setTasks(taskList);
        const cparsList = await contractApi.listCPARS(selectedContractId);
        setCpars(cparsList);
      } catch (err) {
        console.error("Failed to load deliverables", err);
      }
    };
    fetchDeliverables();
  }, [selectedContractId]);

  const handleCreateContract = async () => {
    if (!title.trim() || !number.trim()) return;
    try {
      await contractApi.create({
        contract_number: number.trim(),
        title: title.trim(),
        agency: agency.trim() || undefined,
        status,
      });
      setTitle("");
      setNumber("");
      setAgency("");
      await fetchContracts();
    } catch (err) {
      console.error("Failed to create contract", err);
      setError("Failed to create contract.");
    }
  };

  const handleCreateDeliverable = async () => {
    if (!selectedContractId || !deliverableTitle.trim()) return;
    try {
      await contractApi.createDeliverable(selectedContractId, {
        title: deliverableTitle.trim(),
      });
      setDeliverableTitle("");
      const list = await contractApi.listDeliverables(selectedContractId);
      setDeliverables(list);
    } catch (err) {
      console.error("Failed to create deliverable", err);
      setError("Failed to create deliverable.");
    }
  };

  const handleCreateTask = async () => {
    if (!selectedContractId || !taskTitle.trim()) return;
    try {
      await contractApi.createTask(selectedContractId, { title: taskTitle.trim() });
      setTaskTitle("");
      const list = await contractApi.listTasks(selectedContractId);
      setTasks(list);
    } catch (err) {
      console.error("Failed to create task", err);
      setError("Failed to create task.");
    }
  };

  const handleCreateCPARS = async () => {
    if (!selectedContractId) return;
    try {
      await contractApi.createCPARS(selectedContractId, {
        overall_rating: cparsRating.trim() || undefined,
        notes: cparsNotes.trim() || undefined,
      });
      setCparsRating("");
      setCparsNotes("");
      const list = await contractApi.listCPARS(selectedContractId);
      setCpars(list);
    } catch (err) {
      console.error("Failed to create CPARS review", err);
      setError("Failed to create CPARS review.");
    }
  };

  const selectedContract = useMemo(
    () => contracts.find((c) => c.id === selectedContractId) || null,
    [contracts, selectedContractId]
  );

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Contracts"
        description="Track post-award execution and deliverables"
      />

      <div className="flex-1 p-6 overflow-auto space-y-6">
        {error && <p className="text-destructive">{error}</p>}

        <Card className="border border-border">
          <CardContent className="p-4 space-y-3">
            <p className="text-sm font-medium">New Contract</p>
            <div className="grid grid-cols-4 gap-3">
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
                value={status}
                onChange={(e) => setStatus(e.target.value as ContractStatus)}
              >
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <Button onClick={handleCreateContract}>Create Contract</Button>
          </CardContent>
        </Card>

        <div className="grid grid-cols-3 gap-4">
          <Card className="col-span-1 border border-border">
            <CardContent className="p-4 space-y-2">
              <p className="text-sm font-medium">Contracts</p>
              <div className="space-y-2">
                {contracts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No contracts yet.
                  </p>
                ) : (
                  contracts.map((contract) => (
                    <button
                      key={contract.id}
                      className={`w-full text-left rounded-md border px-3 py-2 text-sm transition-colors ${
                        contract.id === selectedContractId
                          ? "border-primary text-primary"
                          : "border-border text-foreground"
                      }`}
                      onClick={() => setSelectedContractId(contract.id)}
                    >
                      <p className="font-medium">{contract.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {contract.contract_number}
                      </p>
                    </button>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="col-span-2 border border-border">
            <CardContent className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Deliverables</p>
                  <p className="text-xs text-muted-foreground">
                    {selectedContract?.title || "Select a contract"}
                  </p>
                </div>
                {selectedContract && (
                  <Badge variant="outline">{selectedContract.status}</Badge>
                )}
              </div>

              <div className="flex gap-2">
                <input
                  className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
                  placeholder="Deliverable title"
                  value={deliverableTitle}
                  onChange={(e) => setDeliverableTitle(e.target.value)}
                />
                <Button onClick={handleCreateDeliverable}>
                  Add Deliverable
                </Button>
              </div>

              <div className="space-y-2">
                {deliverables.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No deliverables yet.
                  </p>
                ) : (
                  deliverables.map((deliverable) => (
                    <div
                      key={deliverable.id}
                      className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                    >
                      <span>{deliverable.title}</span>
                      <Badge variant="outline">{deliverable.status}</Badge>
                    </div>
                  ))
                )}
              </div>

              <div className="mt-6 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">Tasks</p>
                </div>
                <div className="flex gap-2">
                  <input
                    className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Task title"
                    value={taskTitle}
                    onChange={(e) => setTaskTitle(e.target.value)}
                  />
                  <Button onClick={handleCreateTask}>Add Task</Button>
                </div>
                <div className="space-y-2">
                  {tasks.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No tasks yet.</p>
                  ) : (
                    tasks.map((task) => (
                      <div
                        key={task.id}
                        className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                      >
                        <span>{task.title}</span>
                        <Badge variant="outline">
                          {task.is_complete ? "Complete" : "Open"}
                        </Badge>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="mt-6 space-y-3">
                <p className="text-sm font-medium">CPARS Reviews</p>
                <div className="flex gap-2">
                  <input
                    className="w-40 rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Rating"
                    value={cparsRating}
                    onChange={(e) => setCparsRating(e.target.value)}
                  />
                  <input
                    className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Notes"
                    value={cparsNotes}
                    onChange={(e) => setCparsNotes(e.target.value)}
                  />
                  <Button onClick={handleCreateCPARS}>Add Review</Button>
                </div>
                <div className="space-y-2">
                  {cpars.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No CPARS reviews yet.
                    </p>
                  ) : (
                    cpars.map((review) => (
                      <div
                        key={review.id}
                        className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                      >
                        <span>{review.overall_rating || "Unrated"}</span>
                        <Badge variant="outline">{review.created_at.slice(0, 10)}</Badge>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
