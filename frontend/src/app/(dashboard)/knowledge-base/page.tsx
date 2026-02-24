"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Upload,
  FolderOpen,
  RefreshCw,
  AlertCircle,
  Search,
  Filter,
  Loader2,
  X,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { documentApi, draftApi } from "@/lib/api";
import type { KnowledgeBaseDocument } from "@/types";
import { KBStatsCards } from "./_components/stats-cards";
import { DocumentGrid } from "./_components/document-grid";
import { UploadDropzone } from "./_components/upload-dropzone";

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
      const types = await documentApi.getTypes();
      const defaultType = types[0]?.value || "other";
      await documentApi.upload(file, {
        title: file.name.replace(/\.[^/.]+$/, ""),
        document_type: defaultType,
      });
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

        <KBStatsCards
          total={stats.total}
          ready={stats.ready}
          totalCitations={stats.totalCitations}
          totalSize={stats.totalSize}
        />

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
          <DocumentGrid documents={filteredDocuments} />
        )}

        <UploadDropzone
          isDragOver={isDragOver}
          isUploading={isUploading}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onBrowse={() => fileInputRef.current?.click()}
        />
      </div>
    </div>
  );
}
