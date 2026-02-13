"use client";

import React, { useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useQueryClient } from "@tanstack/react-query";
import {
  useContracts,
  useContractDocuments,
  useContractDetails,
  useCPARSEvidence,
} from "@/hooks/use-contracts";
import { ContractCreationForm } from "./_components/contract-creation-form";
import { DeliverablesTasksPanel } from "./_components/deliverables-tasks-panel";
import { ModificationsPanel } from "./_components/modifications-panel";
import { CLINManagementPanel } from "./_components/clin-management-panel";
import { CPARSEvidencePanel } from "./_components/cpars-evidence-panel";
import { StatusReportsPanel } from "./_components/status-reports-panel";

export default function ContractsPage() {
  const queryClient = useQueryClient();
  const { data: contractsData } = useContracts();
  const { data: documents = [] } = useContractDocuments();
  const [selectedContractId, setSelectedContractId] = useState<number | null>(null);
  const [selectedCparsId, setSelectedCparsId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const contracts = contractsData?.contracts ?? [];

  // Auto-select first contract
  React.useEffect(() => {
    if (contracts.length > 0 && !selectedContractId) {
      setSelectedContractId(contracts[0].id);
    }
  }, [contracts, selectedContractId]);

  const { data: details } = useContractDetails(selectedContractId);
  const { data: cparsEvidence = [] } = useCPARSEvidence(selectedContractId, selectedCparsId);

  const deliverables = details?.deliverables ?? [];
  const tasks = details?.tasks ?? [];
  const modifications = details?.modifications ?? [];
  const clins = details?.clins ?? [];
  const cpars = details?.cpars ?? [];
  const statusReports = details?.statusReports ?? [];

  // Auto-select first CPARS review
  React.useEffect(() => {
    if (cpars.length === 0) {
      setSelectedCparsId(null);
    } else if (!selectedCparsId || !cpars.some((item) => item.id === selectedCparsId)) {
      setSelectedCparsId(cpars[0].id);
    }
  }, [cpars, selectedCparsId]);

  const selectedContract = useMemo(
    () => contracts.find((c) => c.id === selectedContractId) || null,
    [contracts, selectedContractId]
  );
  const contractsById = useMemo(
    () => new Map(contracts.map((contract) => [contract.id, contract])),
    [contracts]
  );

  const refreshContracts = () => queryClient.invalidateQueries({ queryKey: ["contracts"] });
  const refreshDetails = () =>
    queryClient.invalidateQueries({ queryKey: ["contract-details", selectedContractId] });
  const refreshEvidence = () =>
    queryClient.invalidateQueries({ queryKey: ["cpars-evidence", selectedContractId, selectedCparsId] });

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
          onCreated={refreshContracts}
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
                onDeliverablesChange={() => refreshDetails()}
                onTasksChange={() => refreshDetails()}
                onError={setError}
              />

              <ModificationsPanel
                selectedContractId={selectedContractId}
                modifications={modifications}
                onModificationsChange={() => refreshDetails()}
                onError={setError}
              />

              <CLINManagementPanel
                selectedContractId={selectedContractId}
                clins={clins}
                onClinsChange={() => refreshDetails()}
                onError={setError}
              />

              <CPARSEvidencePanel
                selectedContractId={selectedContractId}
                cpars={cpars}
                selectedCparsId={selectedCparsId}
                cparsEvidence={cparsEvidence}
                documents={documents}
                onCparsChange={() => refreshDetails()}
                onSelectedCparsIdChange={setSelectedCparsId}
                onCparsEvidenceChange={() => refreshEvidence()}
                onError={setError}
              />

              <StatusReportsPanel
                selectedContractId={selectedContractId}
                statusReports={statusReports}
                onStatusReportsChange={() => refreshDetails()}
                onError={setError}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
