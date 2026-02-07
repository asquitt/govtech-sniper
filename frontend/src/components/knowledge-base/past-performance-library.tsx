"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Award, Search, Loader2, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { pastPerformanceApi } from "@/lib/api";
import type { PastPerformanceDocument } from "@/types/past-performance";

interface PastPerformanceLibraryProps {
  onSelectDocument: (doc: PastPerformanceDocument) => void;
  selectedId?: number;
}

export function PastPerformanceLibrary({ onSelectDocument, selectedId }: PastPerformanceLibraryProps) {
  const [documents, setDocuments] = useState<PastPerformanceDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchDocuments = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await pastPerformanceApi.list();
      setDocuments(res.data.documents);
    } catch (err) {
      console.error("Failed to fetch past performances:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const filtered = documents.filter((doc) =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.performing_agency?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.contract_number?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatCurrency = (value?: number) =>
    value ? `$${value.toLocaleString()}` : "-";

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString("en-US", { month: "short", year: "numeric" });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div>
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search past performances..."
          className="w-full h-10 pl-10 pr-4 rounded-lg bg-secondary border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
          <FolderOpen className="w-10 h-10 mb-3" />
          <p>{searchQuery ? "No matching documents" : "No past performance documents"}</p>
          <p className="text-sm mt-1">Upload documents with type &quot;Past Performance&quot; to get started</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium">Title</th>
                <th className="py-2 pr-4 font-medium">Contract #</th>
                <th className="py-2 pr-4 font-medium">Agency</th>
                <th className="py-2 pr-4 font-medium">Value</th>
                <th className="py-2 pr-4 font-medium">NAICS</th>
                <th className="py-2 pr-4 font-medium">Period</th>
                <th className="py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((doc) => (
                <tr
                  key={doc.id}
                  className={`border-b border-border/50 hover:bg-secondary/50 transition-colors ${
                    selectedId === doc.id ? "bg-primary/5" : ""
                  }`}
                >
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      <Award className="w-4 h-4 text-amber-400 flex-shrink-0" />
                      <span className="font-medium truncate max-w-[200px]">{doc.title}</span>
                    </div>
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">{doc.contract_number || "-"}</td>
                  <td className="py-3 pr-4 text-muted-foreground truncate max-w-[150px]">
                    {doc.performing_agency || "-"}
                  </td>
                  <td className="py-3 pr-4 text-muted-foreground">{formatCurrency(doc.contract_value)}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{doc.naics_code || "-"}</td>
                  <td className="py-3 pr-4 text-muted-foreground text-xs">
                    {formatDate(doc.period_of_performance_start)} - {formatDate(doc.period_of_performance_end)}
                  </td>
                  <td className="py-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onSelectDocument(doc)}
                    >
                      Edit
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
