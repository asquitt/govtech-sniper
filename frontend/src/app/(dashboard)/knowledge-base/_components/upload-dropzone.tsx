"use client";

import React from "react";
import { Upload, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface UploadDropzoneProps {
  isDragOver: boolean;
  isUploading: boolean;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  onBrowse: () => void;
}

export function UploadDropzone({
  isDragOver,
  isUploading,
  onDragOver,
  onDragLeave,
  onDrop,
  onBrowse,
}: UploadDropzoneProps) {
  return (
    <Card
      className={cn(
        "mt-6 border-dashed transition-colors",
        isDragOver && "border-primary bg-primary/5"
      )}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
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
            onClick={onBrowse}
            disabled={isUploading}
          >
            Browse Files
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
