"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { contractApi, documentApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  ContractAward,
  ContractDeliverable,
  ContractStatus,
  ContractTask,
  CPARSReview,
  ContractStatusReport,
  CPARSEvidence,
  KnowledgeBaseDocument,
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
  const [statusReports, setStatusReports] = useState<ContractStatusReport[]>([]);
  const [documents, setDocuments] = useState<KnowledgeBaseDocument[]>([]);
  const [selectedCparsId, setSelectedCparsId] = useState<number | null>(null);
  const [cparsEvidence, setCparsEvidence] = useState<CPARSEvidence[]>([]);
  const [selectedContractId, setSelectedContractId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [number, setNumber] = useState("");
  const [agency, setAgency] = useState("");
  const [status, setStatus] = useState<ContractStatus>("active");
  const [deliverableTitle, setDeliverableTitle] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [cparsRating, setCparsRating] = useState("");
  const [cparsNotes, setCparsNotes] = useState("");
  const [evidenceDocumentId, setEvidenceDocumentId] = useState<number | null>(null);
  const [evidenceCitation, setEvidenceCitation] = useState("");
  const [evidenceNotes, setEvidenceNotes] = useState("");
  const [reportSummary, setReportSummary] = useState("");
  const [reportRisks, setReportRisks] = useState("");
  const [reportNextSteps, setReportNextSteps] = useState("");
  const [reportStart, setReportStart] = useState("");
  const [reportEnd, setReportEnd] = useState("");
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
    const fetchDeliverables = async () => {
      if (!selectedContractId) return;
      try {
        const list = await contractApi.listDeliverables(selectedContractId);
        setDeliverables(list);
        const taskList = await contractApi.listTasks(selectedContractId);
        setTasks(taskList);
        const cparsList = await contractApi.listCPARS(selectedContractId);
        setCpars(cparsList);
        if (cparsList.length === 0) {
          setSelectedCparsId(null);
          setCparsEvidence([]);
        } else if (!selectedCparsId || !cparsList.some((item) => item.id === selectedCparsId)) {
          setSelectedCparsId(cparsList[0].id);
        }
        const reportList = await contractApi.listStatusReports(selectedContractId);
        setStatusReports(reportList);
      } catch (err) {
        console.error("Failed to load deliverables", err);
      }
    };
    fetchDeliverables();
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
      const created = await contractApi.createCPARS(selectedContractId, {
        overall_rating: cparsRating.trim() || undefined,
        notes: cparsNotes.trim() || undefined,
      });
      setCparsRating("");
      setCparsNotes("");
      const list = await contractApi.listCPARS(selectedContractId);
      setCpars(list);
      setSelectedCparsId(created.id);
    } catch (err) {
      console.error("Failed to create CPARS review", err);
      setError("Failed to create CPARS review.");
    }
  };

  const handleAddEvidence = async () => {
    if (!selectedContractId || !selectedCparsId || !evidenceDocumentId) return;
    try {
      await contractApi.addCPARSEvidence(selectedContractId, selectedCparsId, {
        document_id: evidenceDocumentId,
        citation: evidenceCitation.trim() || undefined,
        notes: evidenceNotes.trim() || undefined,
      });
      setEvidenceDocumentId(null);
      setEvidenceCitation("");
      setEvidenceNotes("");
      const list = await contractApi.listCPARSEvidence(
        selectedContractId,
        selectedCparsId
      );
      setCparsEvidence(list);
    } catch (err) {
      console.error("Failed to add CPARS evidence", err);
      setError("Failed to add CPARS evidence.");
    }
  };

  const handleDeleteEvidence = async (evidenceId: number) => {
    if (!selectedContractId || !selectedCparsId) return;
    try {
      await contractApi.deleteCPARSEvidence(
        selectedContractId,
        selectedCparsId,
        evidenceId
      );
      const list = await contractApi.listCPARSEvidence(
        selectedContractId,
        selectedCparsId
      );
      setCparsEvidence(list);
    } catch (err) {
      console.error("Failed to delete CPARS evidence", err);
      setError("Failed to delete CPARS evidence.");
    }
  };

  const handleCreateStatusReport = async () => {
    if (!selectedContractId) return;
    try {
      await contractApi.createStatusReport(selectedContractId, {
        period_start: reportStart || undefined,
        period_end: reportEnd || undefined,
        summary: reportSummary.trim() || undefined,
        risks: reportRisks.trim() || undefined,
        next_steps: reportNextSteps.trim() || undefined,
      });
      setReportSummary("");
      setReportRisks("");
      setReportNextSteps("");
      setReportStart("");
      setReportEnd("");
      const list = await contractApi.listStatusReports(selectedContractId);
      setStatusReports(list);
    } catch (err) {
      console.error("Failed to create status report", err);
      setError("Failed to create status report.");
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
                    cpars.map((review) => {
                      const isSelected = review.id === selectedCparsId;
                      return (
                        <div
                          key={review.id}
                          className={cn(
                            "flex items-center justify-between rounded-md border px-3 py-2 text-sm cursor-pointer",
                            isSelected
                              ? "border-primary/50 bg-primary/10"
                              : "border-border hover:border-primary/30"
                          )}
                          onClick={() => setSelectedCparsId(review.id)}
                        >
                          <span>{review.overall_rating || "Unrated"}</span>
                          <Badge variant="outline">{review.created_at.slice(0, 10)}</Badge>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              <div className="mt-4 space-y-3">
                <p className="text-sm font-medium">CPARS Evidence</p>
                {!selectedCparsId ? (
                  <p className="text-sm text-muted-foreground">
                    Select a CPARS review to link evidence.
                  </p>
                ) : (
                  <>
                    <div className="grid grid-cols-3 gap-2">
                      <select
                        className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                        value={evidenceDocumentId ?? ""}
                        onChange={(e) =>
                          setEvidenceDocumentId(
                            e.target.value ? Number(e.target.value) : null
                          )
                        }
                      >
                        <option value="">Select document</option>
                        {documents.map((doc) => (
                          <option key={doc.id} value={doc.id}>
                            {doc.title}
                          </option>
                        ))}
                      </select>
                      <input
                        className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                        placeholder="Citation"
                        value={evidenceCitation}
                        onChange={(e) => setEvidenceCitation(e.target.value)}
                      />
                      <input
                        className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                        placeholder="Notes"
                        value={evidenceNotes}
                        onChange={(e) => setEvidenceNotes(e.target.value)}
                      />
                    </div>
                    <Button onClick={handleAddEvidence}>Add Evidence</Button>
                    <div className="space-y-2">
                      {cparsEvidence.length === 0 ? (
                        <p className="text-sm text-muted-foreground">
                          No evidence linked yet.
                        </p>
                      ) : (
                        cparsEvidence.map((evidence) => (
                          <div
                            key={evidence.id}
                            className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                          >
                            <div>
                              <p className="font-medium">
                                {evidence.document_title || `Document ${evidence.document_id}`}
                              </p>
                              {evidence.citation && (
                                <p className="text-xs text-muted-foreground">
                                  {evidence.citation}
                                </p>
                              )}
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteEvidence(evidence.id)}
                            >
                              Remove
                            </Button>
                          </div>
                        ))
                      )}
                    </div>
                  </>
                )}
              </div>

              <div className="mt-6 space-y-3">
                <p className="text-sm font-medium">Status Reports</p>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Period start (YYYY-MM-DD)"
                    value={reportStart}
                    onChange={(e) => setReportStart(e.target.value)}
                  />
                  <input
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Period end (YYYY-MM-DD)"
                    value={reportEnd}
                    onChange={(e) => setReportEnd(e.target.value)}
                  />
                  <input
                    className="col-span-2 rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Summary"
                    value={reportSummary}
                    onChange={(e) => setReportSummary(e.target.value)}
                  />
                  <input
                    className="col-span-2 rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Risks"
                    value={reportRisks}
                    onChange={(e) => setReportRisks(e.target.value)}
                  />
                  <input
                    className="col-span-2 rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Next steps"
                    value={reportNextSteps}
                    onChange={(e) => setReportNextSteps(e.target.value)}
                  />
                </div>
                <Button onClick={handleCreateStatusReport}>Add Status Report</Button>
                <div className="space-y-2">
                  {statusReports.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No status reports yet.
                    </p>
                  ) : (
                    statusReports.map((report) => (
                      <div
                        key={report.id}
                        className="rounded-md border border-border px-3 py-2 text-sm space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span>
                            {report.period_start || "Period"} - {report.period_end || "End"}
                          </span>
                          <Badge variant="outline">
                            {report.created_at.slice(0, 10)}
                          </Badge>
                        </div>
                        {report.summary && (
                          <p className="text-xs text-muted-foreground">
                            {report.summary}
                          </p>
                        )}
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
