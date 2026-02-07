"use client";

import React from "react";
import { FileText, Copy, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface NarrativeGeneratorProps {
  narrative: string;
  onClose: () => void;
}

export function NarrativeGenerator({ narrative, onClose }: NarrativeGeneratorProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(narrative);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-secondary/50 border-b border-border">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-primary" />
          <h4 className="font-medium text-sm">Generated Narrative</h4>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={handleCopy}>
            {copied ? (
              <Check className="w-4 h-4 text-green-400" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
            {copied ? "Copied" : "Copy"}
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>
      <div className="p-4 max-h-96 overflow-y-auto">
        <div className="prose prose-sm prose-invert max-w-none whitespace-pre-wrap text-sm text-foreground">
          {narrative}
        </div>
      </div>
    </div>
  );
}
