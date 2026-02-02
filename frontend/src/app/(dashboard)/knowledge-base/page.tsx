"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Upload,
  FileText,
  FolderOpen,
  MoreHorizontal,
  RefreshCw,
  CheckCircle2,
  Clock,
  AlertCircle,
  Award,
  Briefcase,
  FileCheck,
  Users,
  Search,
  Filter,
  Loader2,
  Sparkles,
  X,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { formatDate, formatFileSize, cn } from "@/lib/utils";
import { documentApi, draftApi } from "@/lib/api";
import type { KnowledgeBaseDocument, DocumentType, ProcessingStatus } from "@/types";

const documentTypeConfig: Record<
  DocumentType,
  { label: string; icon: React.ElementType; color: string }
> = {
  resume: { label: "Resume", icon: Users, color: "text-blue-400" },
  past_performance: { label: "Past Performance", icon: Award, color: "text-amber-400" },
  capability_statement: { label: "Capability", icon: Briefcase, color: "text-emerald-400" },
  technical_spec: { label: "Technical", icon: FileCheck, color: "text-violet-400" },
  case_study: { label: "Case Study", icon: FileText, color: "text-cyan-400" },
  certification: { label: "Certification", icon: Award, color: "text-orange-400" },
  contract: { label: "Contract", icon: FileText, color: "text-pink-400" },
  other: { label: "Other", icon: FileText, color: "text-gray-400" },
};

const statusConfig: Record<
  ProcessingStatus,
  { label: string; icon: React.ElementType; color: string }
> = {
  pending: { label: "Pending", icon: Clock, color: "text-muted-foreground" },
  processing: { label: "Processing", icon: Loader2, color: "text-warning" },
  ready: { label: "Ready", icon: CheckCircle2, color: "text-accent" },
  error: { label: "Error", icon: AlertCircle, color: "text-destructive" },
};

export default function KnowledgeBasePage() {
  const [documents, setDocuments] = useState<KnowledgeBaseDocument[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const docs = await documentApi.list();
      setDocuments(docs);
    } catch (err) {
      console.error("Failed to fetch documents:", err);
      setError("Failed to load documents. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const stats = {
    total: documents.length,
    ready: documents.filter((d) => d.is_ready).length,
    totalCitations: documents.reduce((acc, d) => acc + (d.times_cited || 0), 0),
    totalSize: documents.reduce((acc, d) => acc + (d.file_size_bytes || 0), 0),
  };

  const handleRefreshCache = async () => {
    try {
      setIsRefreshing(true);
      await draftApi.refreshCache();
      await fetchDocuments();
    } catch (err) {
      console.error("Cache refresh failed:", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const file = files[0];
    setIsUploading(true);
    setUploadError(null);

    try {
      // Get document types
      const types = await documentApi.getTypes();
      const defaultType = types[0]?.value || "other";

      // Upload the file
      await documentApi.upload(file, {
        title: file.name.replace(/\.[^/.]+$/, ""),
        document_type: defaultType,
      });

      // Refresh the list
      await fetchDocuments();
    } catch (err) {
      console.error("Upload failed:", err);
      setUploadError("Failed to upload document. Please try again.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFileUpload(e.dataTransfer.files);
  };

  const filteredDocuments = documents.filter(
    (doc) =>
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.original_filename?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (error && !isLoading) {
    return (
      <div className="flex flex-col h-full">
        <Header
          title="Knowledge Base"
          description="Upload documents to power AI-generated citations"
        />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={fetchDocuments}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Knowledge Base"
        description="Upload documents to power AI-generated citations"
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handleRefreshCache} disabled={isRefreshing}>
              {isRefreshing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              Refresh AI Cache
            </Button>
            <Button onClick={() => fileInputRef.current?.click()} disabled={isUploading}>
              {isUploading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Upload className="w-4 h-4" />
              )}
              Upload Document
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.doc,.docx"
              className="hidden"
              onChange={(e) => handleFileUpload(e.target.files)}
            />
          </div>
        }
      />

      <div className="flex-1 p-6 overflow-auto">
        {/* Upload Error */}
        {uploadError && (
          <div className="mb-4 p-4 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center justify-between">
            <p className="text-destructive text-sm">{uploadError}</p>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setUploadError(null)}
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Documents</p>
                  <p className="text-2xl font-bold">{stats.total}</p>
                </div>
                <FolderOpen className="w-8 h-8 text-muted-foreground/30" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-accent/5 to-accent/10 border-accent/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Ready for AI</p>
                  <p className="text-2xl font-bold text-accent">{stats.ready}</p>
                </div>
                <Sparkles className="w-8 h-8 text-accent/30" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Citations</p>
                  <p className="text-2xl font-bold text-primary">
                    {stats.totalCitations}
                  </p>
                </div>
                <FileText className="w-8 h-8 text-primary/30" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Storage Used</p>
                  <p className="text-2xl font-bold">
                    {formatFileSize(stats.totalSize)}
                  </p>
                </div>
                <div className="w-8 h-8 flex items-center justify-center">
                  <Progress value={15} className="w-8 h-8 rounded-full" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Search */}
        <div className="flex items-center gap-4 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search documents..."
              className="w-full h-10 pl-10 pr-4 rounded-lg bg-secondary border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Button variant="outline">
            <Filter className="w-4 h-4" />
            Filter
          </Button>
        </div>

        {/* Loading State */}
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64">
            <FolderOpen className="w-12 h-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground mb-4">
              {searchQuery
                ? "No documents match your search"
                : "No documents uploaded yet"}
            </p>
          </div>
        ) : (
          /* Documents Grid */
          <div className="grid grid-cols-2 gap-4">
            {filteredDocuments.map((doc) => {
              const typeConfig = documentTypeConfig[doc.document_type] || documentTypeConfig.other;
              const status = statusConfig[doc.processing_status] || statusConfig.pending;
              const TypeIcon = typeConfig.icon;
              const StatusIcon = status.icon;

              return (
                <Card
                  key={doc.id}
                  className="hover:border-primary/30 transition-colors cursor-pointer"
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-4">
                      {/* Icon */}
                      <div
                        className={cn(
                          "w-12 h-12 rounded-lg bg-secondary flex items-center justify-center flex-shrink-0",
                          typeConfig.color
                        )}
                      >
                        <TypeIcon className="w-6 h-6" />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <h3 className="font-medium text-foreground truncate">
                              {doc.title}
                            </h3>
                            <p className="text-xs text-muted-foreground truncate">
                              {doc.original_filename}
                            </p>
                          </div>
                          <Button variant="ghost" size="icon" className="flex-shrink-0">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </div>

                        {doc.description && (
                          <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
                            {doc.description}
                          </p>
                        )}

                        <div className="flex items-center gap-4 mt-3">
                          {/* Status */}
                          <div className={cn("flex items-center gap-1 text-xs", status.color)}>
                            <StatusIcon
                              className={cn(
                                "w-3 h-3",
                                doc.processing_status === "processing" && "animate-spin"
                              )}
                            />
                            {status.label}
                          </div>

                          {/* Metadata */}
                          {doc.page_count && (
                            <span className="text-xs text-muted-foreground">
                              {doc.page_count} pages
                            </span>
                          )}
                          <span className="text-xs text-muted-foreground">
                            {formatFileSize(doc.file_size_bytes || 0)}
                          </span>

                          {/* Citations */}
                          {doc.times_cited && doc.times_cited > 0 && (
                            <div className="flex items-center gap-1 text-xs text-primary">
                              <FileText className="w-3 h-3" />
                              {doc.times_cited} citations
                            </div>
                          )}
                        </div>

                        {/* Tags */}
                        {doc.tags && doc.tags.length > 0 && (
                          <div className="flex items-center gap-1 mt-2">
                            {doc.tags.slice(0, 3).map((tag) => (
                              <Badge
                                key={tag}
                                variant="secondary"
                                className="text-[10px] px-1.5"
                              >
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Upload Dropzone */}
        <Card
          className={cn(
            "mt-6 border-dashed transition-colors",
            isDragOver && "border-primary bg-primary/5"
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <CardContent className="p-8">
            <div className="flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center mb-4">
                {isUploading ? (
                  <Loader2 className="w-8 h-8 text-primary animate-spin" />
                ) : (
                  <Upload className="w-8 h-8 text-muted-foreground" />
                )}
              </div>
              <h3 className="font-medium mb-1">
                {isUploading ? "Uploading..." : "Drop files here to upload"}
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                PDF, DOC, DOCX up to 50MB
              </p>
              <Button
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
              >
                Browse Files
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
