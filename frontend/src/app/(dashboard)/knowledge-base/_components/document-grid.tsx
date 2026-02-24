"use client";

import React from "react";
import {
  FileText,
  MoreHorizontal,
  CheckCircle2,
  Clock,
  AlertCircle,
  Award,
  Briefcase,
  FileCheck,
  Users,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { formatFileSize, cn } from "@/lib/utils";
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

export interface DocumentGridProps {
  documents: KnowledgeBaseDocument[];
}

export function DocumentGrid({ documents }: DocumentGridProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {documents.map((doc) => {
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
                <div
                  className={cn(
                    "w-12 h-12 rounded-lg bg-secondary flex items-center justify-center flex-shrink-0",
                    typeConfig.color
                  )}
                >
                  <TypeIcon className="w-6 h-6" />
                </div>

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
                    <div className={cn("flex items-center gap-1 text-xs", status.color)}>
                      <StatusIcon
                        className={cn(
                          "w-3 h-3",
                          doc.processing_status === "processing" && "animate-spin"
                        )}
                      />
                      {status.label}
                    </div>

                    {doc.page_count && (
                      <span className="text-xs text-muted-foreground">
                        {doc.page_count} pages
                      </span>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {formatFileSize(doc.file_size_bytes || 0)}
                    </span>

                    {doc.times_cited && doc.times_cited > 0 && (
                      <div className="flex items-center gap-1 text-xs text-primary">
                        <FileText className="w-3 h-3" />
                        {doc.times_cited} citations
                      </div>
                    )}
                  </div>

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
  );
}
