"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { contractApi, documentApi } from "@/lib/api";
import type {
  ContractAward,
  ContractDeliverable,
  ContractTask,
  CPARSReview,
  ContractStatusReport,
  CPARSEvidence,
  ContractModification,
  ContractCLIN,
  KnowledgeBaseDocument,
} from "@/types";
import { ContractCreationForm } from "./_components/contract-creation-form";
import { DeliverablesTasksPanel } from "./_components/deliverables-tasks-panel";
import { ModificationsPanel } from "./_components/modifications-panel";
import { CLINManagementPanel } from "./_components/clin-management-panel";
import { CPARSEvidencePanel } from "./_components/cpars-evidence-panel";
import { StatusReportsPanel } from "./_components/status-reports-panel";

export default function ContractsPage() {
  const [contracts, setContracts] = useState<ContractAward[]>([]);
  const [deliverables, setDeliverables] = useState<ContractDeliverable[]>([]);
  const [tasks, setTasks] = useState<ContractTask[]>([]);
  const [modifications, setModifications] = useState<ContractModification[]>([]);
  const [clins, setClins] = useState<ContractCLIN[]>([]);
  const [cpars, setCpars] = useState<CPARSReview[]>([]);
  const [statusReports, setStatusReports] = useState<ContractStatusReport[]>([]);
  const [documents, setDocuments] = useState<KnowledgeBaseDocument[]>([]);
  const [selectedCparsId, setSelectedCparsId] = useState<number | null>(null);
  const [cparsEvidence, setCparsEvidence] = useState<CPARSEvidence[]>([]);
  const [selectedContractId, setSelectedContractId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchContracts = useCallback(async () => {
    try {
      const [{ contracts: list }, docs] = await Promise.all([
        contractApi.list(),
        documentApi.list({ ready_only: true }),
      ]);
      setContracts(list);
      setDocuments(docs);
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
    const fetchDetails = async () => {
      if (!selectedContractId) return;
      try {
        const list = await contractApi.listDeliverables(selectedContractId);
        setDeliverables(list);
        const [taskList, modList, clinList, cparsList, reportList] = await Promise.all([
          contractApi.listTasks(selectedContractId),
          contractApi.listModifications(selectedContractId),
          contractApi.listCLINs(selectedContractId),
          contractApi.listCPARS(selectedContractId),
          contractApi.listStatusReports(selectedContractId),
        ]);
        setTasks(taskList);
        setModifications(modList);
        setClins(clinList);
        setCpars(cparsList);
        if (cparsList.length === 0) {
          setSelectedCparsId(null);
          setCparsEvidence([]);
        } else if (!selectedCparsId || !cparsList.some((item) => item.id === selectedCparsId)) {
          setSelectedCparsId(cparsList[0].id);
        }
        setStatusReports(reportList);
      } catch (err) {
        console.error("Failed to load deliverables", err);
      }
    };
    fetchDetails();
  }, [selectedContractId, selectedCparsId]);

  useEffect(() => {
    const fetchEvidence = async () => {
      if (!selectedContractId || !selectedCparsId) return;
      try {
        const list = await contractApi.listCPARSEvidence(
          selectedContractId,
          selectedCparsId
        );
        setCparsEvidence(list);
      } catch (err) {
        console.error("Failed to load CPARS evidence", err);
      }
    };
    fetchEvidence();
  }, [selectedContractId, selectedCparsId]);

  const selectedContract = useMemo(
    () => contracts.find((c) => c.id === selectedContractId) || null,
    [contracts, selectedContractId]
  );
  const contractsById = useMemo(
    () => new Map(contracts.map((contract) => [contract.id, contract])),
    [contracts]
  );

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Contracts"
        description="Track post-award execution and deliverables"
      />

      <div className="flex-1 p-6 overflow-auto space-y-6">
        {error && <p className="text-destructive">{error}</p>}

        <ContractCreationForm
          contracts={contracts}
          onCreated={fetchContracts}
          onError={setError}
        />

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
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{contract.contract_number}</span>
                        {contract.contract_type && (
                          <Badge variant="outline">{contract.contract_type}</Badge>
                        )}
                      </div>
                      {contract.parent_contract_id && (
                        <p className="text-xs text-muted-foreground">
                          Parent:{" "}
                          {contractsById.get(contract.parent_contract_id)
                            ?.contract_number || "Unknown"}
                        </p>
                      )}
                    </button>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="col-span-2 border border-border">
            <CardContent className="p-4 space-y-3">
              <DeliverablesTasksPanel
                selectedContractId={selectedContractId}
                selectedContract={selectedContract}
                deliverables={deliverables}
                tasks={tasks}
                contracts={contracts}
                onDeliverablesChange={setDeliverables}
                onTasksChange={setTasks}
                onError={setError}
              />

              <ModificationsPanel
                selectedContractId={selectedContractId}
                modifications={modifications}
                onModificationsChange={setModifications}
                onError={setError}
              />

              <CLINManagementPanel
                selectedContractId={selectedContractId}
                clins={clins}
                onClinsChange={setClins}
                onError={setError}
              />

              <CPARSEvidencePanel
                selectedContractId={selectedContractId}
                cpars={cpars}
                selectedCparsId={selectedCparsId}
                cparsEvidence={cparsEvidence}
                documents={documents}
                onCparsChange={setCpars}
                onSelectedCparsIdChange={setSelectedCparsId}
                onCparsEvidenceChange={setCparsEvidence}
                onError={setError}
              />

              <StatusReportsPanel
                selectedContractId={selectedContractId}
                statusReports={statusReports}
                onStatusReportsChange={setStatusReports}
                onError={setError}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
