"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle2,
  AlertCircle,
  Save,
  Plus,
  Link2,
  Package,
  ArrowLeft,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { draftApi, documentApi, exportApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type {
  Proposal,
  ProposalSection,
  SectionEvidence,
  SubmissionPackage,
  KnowledgeBaseDocument,
} from "@/types";

export default function ProposalWorkspacePage() {
  const params = useParams();
  const proposalId = parseInt(params.proposalId as string, 10);

  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [sections, setSections] = useState<ProposalSection[]>([]);
  const [selectedSectionId, setSelectedSectionId] = useState<number | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [evidence, setEvidence] = useState<SectionEvidence[]>([]);
  const [documents, setDocuments] = useState<KnowledgeBaseDocument[]>([]);
  const [submissionPackages, setSubmissionPackages] = useState<SubmissionPackage[]>([]);
  const [newPackageTitle, setNewPackageTitle] = useState("");
  const [newPackageDueDate, setNewPackageDueDate] = useState("");
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
      const [proposalData, sectionData, packageData, docs] = await Promise.all([
        draftApi.getProposal(proposalId),
        draftApi.listSections(proposalId),
        draftApi.listSubmissionPackages(proposalId),
        documentApi.list({ ready_only: true }),
      ]);

      setProposal(proposalData);
      setSections(sectionData);
      setSubmissionPackages(packageData);
      setDocuments(docs);

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
            <Card className="border border-border h-full">
              <CardContent className="p-4 h-full flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-sm font-semibold text-foreground">Sections</p>
                    <p className="text-xs text-muted-foreground">
                      {proposal.completed_sections}/{proposal.total_sections} complete
                    </p>
                  </div>
                </div>
                <ScrollArea className="flex-1 -mx-2 px-2">
                  <div className="space-y-2">
                    {sections.length === 0 ? (
                      <div className="text-sm text-muted-foreground">No sections yet.</div>
                    ) : (
                      sections.map((section) => (
                        <button
                          key={section.id}
                          type="button"
                          onClick={() => setSelectedSectionId(section.id)}
                          className={`w-full text-left rounded-lg border px-3 py-2 transition-colors ${
                            selectedSectionId === section.id
                              ? "border-primary/40 bg-primary/10"
                              : "border-border hover:border-primary/30"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs text-muted-foreground font-mono">
                              {section.section_number}
                            </span>
                            <Badge variant="outline" className="text-[10px]">
                              {section.status}
                            </Badge>
                          </div>
                          <p className="text-sm text-foreground mt-1 line-clamp-2">
                            {section.title}
                          </p>
                        </button>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-6 h-full">
            <Card className="border border-border h-full flex flex-col">
              <CardContent className="p-4 flex-1 flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-sm font-semibold text-foreground">
                      {selectedSection ? selectedSection.title : "Select a Section"}
                    </p>
                    {selectedSection && (
                      <p className="text-xs text-muted-foreground">
                        {selectedSection.section_number}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" onClick={handleApproveSection} disabled={!selectedSection}>
                      <CheckCircle2 className="w-4 h-4" />
                      Approve
                    </Button>
                    <Button onClick={handleSaveSection} disabled={!selectedSection || isSaving}>
                      <Save className="w-4 h-4" />
                      Save
                    </Button>
                  </div>
                </div>
                <textarea
                  className="flex-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  placeholder="Write or edit proposal content..."
                  value={editorContent}
                  onChange={(e) => setEditorContent(e.target.value)}
                  disabled={!selectedSection}
                />
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-3 h-full space-y-6">
            <Card className="border border-border">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <Link2 className="w-4 h-4 text-primary" />
                  <p className="text-sm font-semibold">Evidence</p>
                </div>
                <div className="space-y-2 text-xs text-muted-foreground">
                  {evidence.length === 0 ? (
                    <p>No evidence linked yet.</p>
                  ) : (
                    evidence.map((link) => (
                      <div key={link.id} className="border border-border rounded-md p-2">
                        <p className="text-sm text-foreground">
                          {link.document_title || link.document_filename || "Document"}
                        </p>
                        {link.citation && <p className="text-xs">{link.citation}</p>}
                      </div>
                    ))
                  )}
                </div>
                <div className="space-y-2">
                  <select
                    className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                    value={selectedDocumentId ?? ""}
                    onChange={(e) => setSelectedDocumentId(Number(e.target.value) || null)}
                  >
                    <option value="">Select document</option>
                    {documents.map((doc) => (
                      <option key={doc.id} value={doc.id}>
                        {doc.title}
                      </option>
                    ))}
                  </select>
                  <input
                    className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Citation or page reference"
                    value={citationText}
                    onChange={(e) => setCitationText(e.target.value)}
                  />
                  <input
                    className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Notes"
                    value={notesText}
                    onChange={(e) => setNotesText(e.target.value)}
                  />
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={handleAddEvidence}
                    disabled={!selectedSection || !selectedDocumentId}
                  >
                    <Plus className="w-4 h-4" />
                    Add Evidence
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card className="border border-border">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <Package className="w-4 h-4 text-primary" />
                  <p className="text-sm font-semibold">Submission Packages</p>
                </div>
                <div className="space-y-2">
                  {submissionPackages.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No packages yet.</p>
                  ) : (
                    submissionPackages.map((pkg) => (
                      <div key={pkg.id} className="border border-border rounded-md p-2">
                        <p className="text-sm text-foreground">{pkg.title}</p>
                        <p className="text-xs text-muted-foreground">
                          Status: {pkg.status}
                        </p>
                        {pkg.due_date && (
                          <p className="text-xs text-muted-foreground">
                            Due {formatDate(pkg.due_date)}
                          </p>
                        )}
                      </div>
                    ))
                  )}
                </div>
                <div className="space-y-2">
                  <input
                    className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Package title"
                    value={newPackageTitle}
                    onChange={(e) => setNewPackageTitle(e.target.value)}
                  />
                  <input
                    className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                    placeholder="Due date (YYYY-MM-DD)"
                    value={newPackageDueDate}
                    onChange={(e) => setNewPackageDueDate(e.target.value)}
                  />
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={handleCreatePackage}
                  >
                    <Plus className="w-4 h-4" />
                    Create Package
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
