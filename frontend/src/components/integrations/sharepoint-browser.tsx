"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  FolderOpen,
  FileText,
  ChevronRight,
  ArrowLeft,
  Download,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { sharepointApi } from "@/lib/api";
import type { SharePointFile, SharePointStatus } from "@/types";

interface SharePointBrowserProps {
  onFileSelect?: (file: SharePointFile) => void;
}

export function SharePointBrowser({ onFileSelect }: SharePointBrowserProps) {
  const [status, setStatus] = useState<SharePointStatus | null>(null);
  const [files, setFiles] = useState<SharePointFile[]>([]);
  const [currentPath, setCurrentPath] = useState("/");
  const [pathStack, setPathStack] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      const s = await sharepointApi.status();
      setStatus(s);
      return s;
    } catch {
      setStatus({ configured: false, enabled: false, connected: false });
      return null;
    }
  }, []);

  const loadFiles = useCallback(async (path: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await sharepointApi.browse(path);
      setFiles(data);
      setCurrentPath(path);
    } catch {
      setError("Failed to load files from SharePoint");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      const s = await loadStatus();
      if (s?.connected) {
        await loadFiles("/");
      } else {
        setLoading(false);
      }
    };
    init();
  }, [loadStatus, loadFiles]);

  const navigateToFolder = (folder: SharePointFile) => {
    const newPath =
      currentPath === "/" ? `/${folder.name}` : `${currentPath}/${folder.name}`;
    setPathStack((prev) => [...prev, currentPath]);
    loadFiles(newPath);
  };

  const navigateBack = () => {
    const previousPath = pathStack[pathStack.length - 1] || "/";
    setPathStack((prev) => prev.slice(0, -1));
    loadFiles(previousPath);
  };

  const handleDownload = async (file: SharePointFile) => {
    try {
      const blob = await sharepointApi.download(file.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = file.name;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError(`Failed to download ${file.name}`);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return "-";
    const units = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
  };

  // Not configured state
  if (!loading && status && !status.configured) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center">
        <AlertCircle className="w-12 h-12 text-muted-foreground mb-3" />
        <h3 className="text-sm font-semibold text-foreground mb-1">
          SharePoint Not Configured
        </h3>
        <p className="text-xs text-muted-foreground max-w-sm">
          Set up your SharePoint integration in Settings to browse and export
          files.
        </p>
      </div>
    );
  }

  // Connection status bar
  const statusBadge = status?.connected ? (
    <Badge variant="outline" className="gap-1 text-xs">
      <CheckCircle2 className="w-3 h-3 text-green-500" /> Connected
    </Badge>
  ) : status?.configured ? (
    <Badge variant="destructive" className="gap-1 text-xs">
      <AlertCircle className="w-3 h-3" /> Not Connected
    </Badge>
  ) : null;

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {currentPath !== "/" && (
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={navigateBack}>
              <ArrowLeft className="w-4 h-4" />
            </Button>
          )}
          <span className="text-sm font-medium text-foreground truncate">
            {currentPath}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {statusBadge}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => loadFiles(currentPath)}
          >
            <RefreshCw className="w-3 h-3" />
          </Button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}

      {/* File list */}
      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 rounded bg-muted animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="space-y-1">
          {files.length === 0 && (
            <p className="text-sm text-muted-foreground py-4 text-center">
              No files in this folder
            </p>
          )}
          {files.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-3 p-2 rounded-lg hover:bg-secondary cursor-pointer transition-colors"
              onClick={() => {
                if (file.is_folder) {
                  navigateToFolder(file);
                } else {
                  onFileSelect?.(file);
                }
              }}
            >
              {file.is_folder ? (
                <FolderOpen className="w-4 h-4 text-primary flex-shrink-0" />
              ) : (
                <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-foreground truncate">{file.name}</p>
                {file.last_modified && (
                  <p className="text-xs text-muted-foreground">
                    {new Date(file.last_modified).toLocaleDateString()}
                  </p>
                )}
              </div>
              <span className="text-xs text-muted-foreground">
                {file.is_folder ? "" : formatSize(file.size)}
              </span>
              {file.is_folder ? (
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              ) : (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDownload(file);
                  }}
                >
                  <Download className="w-3 h-3" />
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
