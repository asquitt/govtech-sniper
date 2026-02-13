"use client";

import React, { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { contractApi } from "@/lib/api";
import type {
  ContractAward,
  ContractDeliverable,
  ContractTask,
} from "@/types";

interface DeliverablesTasksPanelProps {
  selectedContractId: number | null;
  selectedContract: ContractAward | null;
  deliverables: ContractDeliverable[];
  tasks: ContractTask[];
  contracts: ContractAward[];
  onDeliverablesChange: (deliverables: ContractDeliverable[]) => void;
  onTasksChange: (tasks: ContractTask[]) => void;
  onError: (msg: string) => void;
}

export function DeliverablesTasksPanel({
  selectedContractId,
  selectedContract,
  deliverables,
  tasks,
  contracts,
  onDeliverablesChange,
  onTasksChange,
  onError,
}: DeliverablesTasksPanelProps) {
  const [deliverableTitle, setDeliverableTitle] = useState("");
  const [taskTitle, setTaskTitle] = useState("");

  const contractsById = useMemo(
    () => new Map(contracts.map((contract) => [contract.id, contract])),
    [contracts]
  );
  const selectedParentContract = useMemo(() => {
    if (!selectedContract?.parent_contract_id) return null;
    return contractsById.get(selectedContract.parent_contract_id) || null;
  }, [contractsById, selectedContract]);
  const childContracts = useMemo(() => {
    if (!selectedContract) return [];
    return contracts.filter(
      (contract) => contract.parent_contract_id === selectedContract.id
    );
  }, [contracts, selectedContract]);

  const handleCreateDeliverable = async () => {
    if (!selectedContractId || !deliverableTitle.trim()) return;
    try {
      await contractApi.createDeliverable(selectedContractId, {
        title: deliverableTitle.trim(),
      });
      setDeliverableTitle("");
      const list = await contractApi.listDeliverables(selectedContractId);
      onDeliverablesChange(list);
    } catch (err) {
      console.error("Failed to create deliverable", err);
      onError("Failed to create deliverable.");
    }
  };

  const handleCreateTask = async () => {
    if (!selectedContractId || !taskTitle.trim()) return;
    try {
      await contractApi.createTask(selectedContractId, { title: taskTitle.trim() });
      setTaskTitle("");
      const list = await contractApi.listTasks(selectedContractId);
      onTasksChange(list);
    } catch (err) {
      console.error("Failed to create task", err);
      onError("Failed to create task.");
    }
  };

  return (
    <>
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
              <div className="flex items-center gap-2">
                <Badge variant="outline">{deliverable.status}</Badge>
                {deliverable.risk_flag && (
                  <Badge
                    variant={
                      deliverable.risk_flag === "overdue"
                        ? "destructive"
                        : deliverable.risk_flag === "due_soon"
                        ? "warning"
                        : "outline"
                    }
                  >
                    {deliverable.risk_flag.replace("_", " ")}
                  </Badge>
                )}
              </div>
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
        <p className="text-sm font-medium">Hierarchy</p>
        {!selectedContract ? (
          <p className="text-sm text-muted-foreground">
            Select a contract to manage hierarchy.
          </p>
        ) : (
          <>
            <div className="rounded-md border border-border px-3 py-2 text-sm">
              <p className="font-medium">Parent Contract</p>
              <p className="text-xs text-muted-foreground">
                {selectedParentContract
                  ? `${selectedParentContract.contract_number} - ${selectedParentContract.title}`
                  : "Top-level contract"}
              </p>
            </div>
            <div className="rounded-md border border-border px-3 py-2 text-sm space-y-2">
              <p className="font-medium">Child Orders</p>
              {childContracts.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No child orders linked.
                </p>
              ) : (
                childContracts.map((childContract) => (
                  <div
                    key={childContract.id}
                    className="flex items-center justify-between text-xs"
                  >
                    <span>
                      {childContract.contract_number} - {childContract.title}
                    </span>
                    <Badge variant="outline">
                      {childContract.contract_type || "task_order"}
                    </Badge>
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </div>
    </>
  );
}
