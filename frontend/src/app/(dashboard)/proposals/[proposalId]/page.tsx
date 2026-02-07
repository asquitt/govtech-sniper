"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AlertCircle, ArrowLeft } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { FocusDocumentSelector } from "@/components/proposals/focus-document-selector";
import { SectionSidebar } from "./_components/section-sidebar";
import { SectionEditor } from "./_components/section-editor";
import { EvidencePanel } from "./_components/evidence-panel";
import { WordAssistantPanel } from "./_components/word-assistant-panel";
import { GraphicsPanel } from "./_components/graphics-panel";
import { SubmissionPanel } from "./_components/submission-panel";
import { draftApi, documentApi, exportApi, wordAddinApi, graphicsApi } from "@/lib/api";
import type {
  Proposal,
  ProposalSection,
  SectionEvidence,
  SubmissionPackage,
  KnowledgeBaseDocument,
  WordAddinSession,
  WordAddinEvent,
  ProposalGraphicRequest,
} from "@/types";

export default function ProposalWorkspacePage() {
  const params = useParams();
  const proposalId = parseInt(params.proposalId as string, 10);

  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [sections, setSections] = useState<ProposalSection[]>([]);
  const [selectedSectionId, setSelectedSectionId] = useState<number | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [writingPlan, setWritingPlan] = useState("");
  const [isSavingPlan, setIsSavingPlan] = useState(false);
  const [evidence, setEvidence] = useState<SectionEvidence[]>([]);
  const [documents, setDocuments] = useState<KnowledgeBaseDocument[]>([]);
  const [submissionPackages, setSubmissionPackages] = useState<SubmissionPackage[]>([]);
  const [newPackageTitle, setNewPackageTitle] = useState("");
  const [newPackageDueDate, setNewPackageDueDate] = useState("");
  const [wordSessions, setWordSessions] = useState<WordAddinSession[]>([]);
  const [wordEvents, setWordEvents] = useState<Record<number, WordAddinEvent[]>>({});
  const [wordDocName, setWordDocName] = useState("");
  const [isSyncingWord, setIsSyncingWord] = useState(false);
  const [updatingWordSessionId, setUpdatingWordSessionId] = useState<number | null>(null);
  const [graphicsRequests, setGraphicsRequests] = useState<ProposalGraphicRequest[]>([]);
  const [graphicsTitle, setGraphicsTitle] = useState("");
  const [graphicsDescription, setGraphicsDescription] = useState("");
  const [graphicsSectionId, setGraphicsSectionId] = useState<number | null>(null);
  const [graphicsDueDate, setGraphicsDueDate] = useState("");
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [citationText, setCitationText] = useState("");
  const [notesText, setNotesText] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const selectedSection = useMemo(
    () => sections.find((section) => section.id === selectedSectionId) || null,
    [sections, selectedSectionId]
  );

  const refreshWorkspace = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [proposalData, sectionData, packageData, docs, sessions, graphics] = await Promise.all([
        draftApi.getProposal(proposalId),
        draftApi.listSections(proposalId),
        draftApi.listSubmissionPackages(proposalId),
        documentApi.list({ ready_only: true }),
        wordAddinApi.listSessions({ proposal_id: proposalId }),
        graphicsApi.listRequests({ proposal_id: proposalId }),
      ]);

      setProposal(proposalData);
      setSections(sectionData);
      setSubmissionPackages(packageData);
      setDocuments(docs);
      setWordSessions(sessions);
      setGraphicsRequests(graphics);

      setSelectedSectionId((current) =>
        current ?? (sectionData.length > 0 ? sectionData[0].id : null)
      );
    } catch (err) {
      console.error("Failed to load proposal workspace", err);
      setError("Failed to load proposal workspace.");
    } finally {
      setIsLoading(false);
    }
  }, [proposalId]);

  useEffect(() => {
    refreshWorkspace();
  }, [refreshWorkspace]);

  useEffect(() => {
    const fetchEvidence = async () => {
      if (!selectedSectionId) {
        setEvidence([]);
        setEditorContent("");
        return;
      }
      try {
        const [links] = await Promise.all([
          draftApi.listSectionEvidence(selectedSectionId),
        ]);
        setEvidence(links);
      } catch (err) {
        console.error("Failed to load evidence", err);
      }

      const section = sections.find((s) => s.id === selectedSectionId);
      if (section) {
        setEditorContent(section.final_content || section.generated_content?.clean_text || "");
        setWritingPlan(section.writing_plan || "");
      }
    };

    fetchEvidence();
  }, [selectedSectionId, sections]);

  const handleSaveSection = async () => {
    if (!selectedSection) return;
    try {
      setIsSaving(true);
      const updated = await draftApi.updateSection(selectedSection.id, {
        final_content: editorContent,
      });
      setSections((prev) =>
        prev.map((section) => (section.id === updated.id ? updated : section))
      );
    } catch (err) {
      console.error("Failed to save section", err);
      setError("Failed to save section.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveWritingPlan = async () => {
    if (!selectedSection) return;
    try {
      setIsSavingPlan(true);
      const updated = await draftApi.updateSection(selectedSection.id, {
        writing_plan: writingPlan,
      });
      setSections((prev) =>
        prev.map((section) => (section.id === updated.id ? updated : section))
      );
    } catch (err) {
      console.error("Failed to save writing plan", err);
      setError("Failed to save writing plan.");
    } finally {
      setIsSavingPlan(false);
    }
  };

  const handleApproveSection = async () => {
    if (!selectedSection) return;
    try {
      setIsSaving(true);
      const updated = await draftApi.updateSection(selectedSection.id, {
        status: "approved",
      });
      setSections((prev) =>
        prev.map((section) => (section.id === updated.id ? updated : section))
      );
    } catch (err) {
      console.error("Failed to approve section", err);
      setError("Failed to approve section.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddEvidence = async () => {
    if (!selectedSection || !selectedDocumentId) return;
    try {
      const link = await draftApi.addSectionEvidence(selectedSection.id, {
        document_id: selectedDocumentId,
        citation: citationText || undefined,
        notes: notesText || undefined,
      });
      setEvidence((prev) => [...prev, link]);
      setCitationText("");
      setNotesText("");
    } catch (err) {
      console.error("Failed to add evidence", err);
      setError("Failed to add evidence.");
    }
  };

  const handleCreatePackage = async () => {
    if (!newPackageTitle) return;
    try {
      const created = await draftApi.createSubmissionPackage(proposalId, {
        title: newPackageTitle,
        due_date: newPackageDueDate || undefined,
      });
      setSubmissionPackages((prev) => [created, ...prev]);
      setNewPackageTitle("");
      setNewPackageDueDate("");
    } catch (err) {
      console.error("Failed to create submission package", err);
      setError("Failed to create submission package.");
    }
  };

  const handleCreateWordSession = async () => {
    if (!wordDocName.trim()) return;
    try {
      const created = await wordAddinApi.createSession({
        proposal_id: proposalId,
        document_name: wordDocName.trim(),
      });
      setWordSessions((prev) => [created, ...prev]);
      setWordDocName("");
    } catch (err) {
      console.error("Failed to create Word add-in session", err);
      setError("Failed to create Word add-in session.");
    }
  };

  const handleSyncWordSession = async (sessionId: number) => {
    try {
      setIsSyncingWord(true);
      await wordAddinApi.createEvent(sessionId, {
        event_type: "sync",
        payload: { proposal_id: proposalId, section_count: sections.length },
      });
      const events = await wordAddinApi.listEvents(sessionId);
      setWordEvents((prev) => ({ ...prev, [sessionId]: events }));
    } catch (err) {
      console.error("Failed to sync Word add-in", err);
      setError("Failed to sync Word add-in.");
    } finally {
      setIsSyncingWord(false);
    }
  };

  const handleUpdateWordSessionStatus = async (
    sessionId: number,
    status: WordAddinSession["status"]
  ) => {
    try {
      setUpdatingWordSessionId(sessionId);
      const updated = await wordAddinApi.updateSession(sessionId, { status });
      setWordSessions((prev) =>
        prev.map((session) => (session.id === sessionId ? updated : session))
      );
    } catch (err) {
      console.error("Failed to update Word add-in session", err);
      setError("Failed to update Word add-in session.");
    } finally {
      setUpdatingWordSessionId(null);
    }
  };

  const handleLoadWordEvents = async (sessionId: number) => {
    try {
      const events = await wordAddinApi.listEvents(sessionId);
      setWordEvents((prev) => ({ ...prev, [sessionId]: events }));
    } catch (err) {
      console.error("Failed to load Word add-in events", err);
      setError("Failed to load Word add-in events.");
    }
  };

  const handleCreateGraphicsRequest = async () => {
    if (!graphicsTitle.trim()) return;
    try {
      const created = await graphicsApi.createRequest({
        proposal_id: proposalId,
        title: graphicsTitle.trim(),
        description: graphicsDescription || undefined,
        section_id: graphicsSectionId || undefined,
        due_date: graphicsDueDate || undefined,
      });
      setGraphicsRequests((prev) => [created, ...prev]);
      setGraphicsTitle("");
      setGraphicsDescription("");
      setGraphicsSectionId(null);
      setGraphicsDueDate("");
    } catch (err) {
      console.error("Failed to create graphics request", err);
      setError("Failed to create graphics request.");
    }
  };

  const handleUpdateGraphicsStatus = async (
    requestId: number,
    status: ProposalGraphicRequest["status"]
  ) => {
    try {
      const updated = await graphicsApi.updateRequest(requestId, { status });
      setGraphicsRequests((prev) =>
        prev.map((request) => (request.id === requestId ? updated : request))
      );
    } catch (err) {
      console.error("Failed to update graphics request", err);
      setError("Failed to update graphics request.");
    }
  };

  const handleRemoveGraphicsRequest = async (requestId: number) => {
    try {
      await graphicsApi.removeRequest(requestId);
      setGraphicsRequests((prev) => prev.filter((request) => request.id !== requestId));
    } catch (err) {
      console.error("Failed to remove graphics request", err);
      setError("Failed to remove graphics request.");
    }
  };

  const handleExport = async (format: "docx" | "pdf") => {
    if (!proposal) return;
    try {
      const blob = format === "docx"
        ? await exportApi.exportProposalDocx(proposal.id)
        : await exportApi.exportProposalPdf(proposal.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${proposal.title}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Export failed", err);
      setError("Failed to export proposal.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Loading Proposal..." description="Fetching workspace data" />
        <div className="flex-1 flex items-center justify-center">
          <AlertCircle className="w-8 h-8 animate-pulse text-primary" />
        </div>
      </div>
    );
  }

  if (error || !proposal) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Proposal Workspace" description="Unable to load proposal" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <AlertCircle className="w-10 h-10 text-destructive mx-auto mb-4" />
            <p className="text-destructive mb-4">{error || "Proposal not found"}</p>
            <Button asChild>
              <Link href="/proposals">
                <ArrowLeft className="w-4 h-4" />
                Back to Proposals
              </Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title={proposal.title}
        description={`Proposal Workspace • ${proposal.status}`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" asChild>
              <Link href="/proposals">
                <ArrowLeft className="w-4 h-4" />
                Back
              </Link>
            </Button>
            <FocusDocumentSelector
              proposalId={proposalId}
              documents={documents}
            />
            <Button variant="outline" asChild>
              <Link href={`/proposals/${proposal.id}/versions`}>
                Versions
              </Link>
            </Button>
            <Button variant="outline" onClick={() => handleExport("docx")}>
              Export DOCX
            </Button>
            <Button variant="outline" onClick={() => handleExport("pdf")}>
              Export PDF
            </Button>
          </div>
        }
      />

      <div className="flex-1 p-6 overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full">
          <div className="lg:col-span-3 h-full">
            <SectionSidebar
              proposal={proposal}
              sections={sections}
              selectedSectionId={selectedSectionId}
              onSelectSection={setSelectedSectionId}
              proposalId={proposalId}
              onOutlineApproved={refreshWorkspace}
            />
          </div>

          <div className="lg:col-span-6 h-full">
            <SectionEditor
              selectedSection={selectedSection}
              editorContent={editorContent}
              onEditorContentChange={setEditorContent}
              writingPlan={writingPlan}
              onWritingPlanChange={setWritingPlan}
              onSaveWritingPlan={handleSaveWritingPlan}
              isSavingPlan={isSavingPlan}
              onSave={handleSaveSection}
              onApprove={handleApproveSection}
              isSaving={isSaving}
            />
          </div>

          <div className="lg:col-span-3 h-full space-y-6">
            <EvidencePanel
              evidence={evidence}
              documents={documents}
              selectedDocumentId={selectedDocumentId}
              onDocumentChange={setSelectedDocumentId}
              citationText={citationText}
              onCitationChange={setCitationText}
              notesText={notesText}
              onNotesChange={setNotesText}
              onAddEvidence={handleAddEvidence}
              disabled={!selectedSection}
            />

            <WordAssistantPanel
              sessions={wordSessions}
              events={wordEvents}
              docName={wordDocName}
              onDocNameChange={setWordDocName}
              onCreateSession={handleCreateWordSession}
              onSyncSession={handleSyncWordSession}
              onLoadEvents={handleLoadWordEvents}
              onUpdateStatus={handleUpdateWordSessionStatus}
              isSyncing={isSyncingWord}
              updatingSessionId={updatingWordSessionId}
            />

            <GraphicsPanel
              requests={graphicsRequests}
              sections={sections}
              title={graphicsTitle}
              onTitleChange={setGraphicsTitle}
              description={graphicsDescription}
              onDescriptionChange={setGraphicsDescription}
              sectionId={graphicsSectionId}
              onSectionIdChange={setGraphicsSectionId}
              dueDate={graphicsDueDate}
              onDueDateChange={setGraphicsDueDate}
              onCreateRequest={handleCreateGraphicsRequest}
              onUpdateStatus={handleUpdateGraphicsStatus}
              onRemoveRequest={handleRemoveGraphicsRequest}
            />

            <SubmissionPanel
              packages={submissionPackages}
              title={newPackageTitle}
              onTitleChange={setNewPackageTitle}
              dueDate={newPackageDueDate}
              onDueDateChange={setNewPackageDueDate}
              onCreatePackage={handleCreatePackage}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
