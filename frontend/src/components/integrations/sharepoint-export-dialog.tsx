"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Upload, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { sharepointApi } from "@/lib/api";
import type { SharePointUploadResult } from "@/types";

interface SharePointExportDialogProps {
  proposalId: number;
  proposalTitle: string;
  onClose: () => void;
}

export function SharePointExportDialog({
  proposalId,
  proposalTitle,
  onClose,
}: SharePointExportDialogProps) {
  const [folder, setFolder] = useState("/Proposals");
  const [format, setFormat] = useState<"docx" | "pdf">("docx");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SharePointUploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await sharepointApi.export(proposalId, folder, format);
      setResult(res);
    } catch {
      setError("Failed to export to SharePoint. Check your integration settings.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 rounded-lg border border-border bg-card space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">
          Export to SharePoint
        </h3>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Close
        </Button>
      </div>

      <p className="text-xs text-muted-foreground">
        Export &ldquo;{proposalTitle}&rdquo; to your SharePoint document library.
      </p>

      {!result ? (
        <div className="space-y-3">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">
              Target Folder
            </label>
            <input
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={folder}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFolder(e.target.value)}
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1 block">
              Format
            </label>
            <div className="flex gap-2">
              {(["docx", "pdf"] as const).map((f) => (
                <Button
                  key={f}
                  variant={format === f ? "default" : "outline"}
                  size="sm"
                  onClick={() => setFormat(f)}
                >
                  {f.toUpperCase()}
                </Button>
              ))}
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-xs text-destructive">
              <AlertCircle className="w-3 h-3" />
              {error}
            </div>
          )}

          <Button onClick={handleExport} disabled={loading} className="w-full">
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4 mr-2" />
                Export to SharePoint
              </>
            )}
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle2 className="w-5 h-5" />
            <span className="text-sm font-medium">Exported successfully!</span>
          </div>
          <div className="text-xs text-muted-foreground space-y-1">
            <p>
              <strong>File:</strong> {result.name}
            </p>
            <p>
              <strong>Size:</strong>{" "}
              {(result.size / 1024).toFixed(1)} KB
            </p>
            {result.web_url && (
              <a
                href={result.web_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline"
              >
                Open in SharePoint
              </a>
            )}
          </div>
          <Button variant="outline" onClick={onClose} className="w-full">
            Done
          </Button>
        </div>
      )}
    </div>
  );
}
