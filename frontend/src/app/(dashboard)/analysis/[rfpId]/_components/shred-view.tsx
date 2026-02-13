"use client";

import React from "react";
import { CheckCircle2, FileText, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ComplianceRequirement } from "@/types";

interface ShredViewProps {
  requirements: ComplianceRequirement[];
  isGenerating: boolean;
  generatingId: string | undefined;
  onSelectRequirement: (req: ComplianceRequirement) => void;
  onGenerate: (req: ComplianceRequirement) => void;
  onSwitchToList: () => void;
}

export function ShredView({
  requirements,
  isGenerating,
  generatingId,
  onSelectRequirement,
  onGenerate,
  onSwitchToList,
}: ShredViewProps) {
  const grouped = requirements.reduce((acc, req) => {
    const category = req.category || "Other";
    if (!acc[category]) acc[category] = [];
    acc[category].push(req);
    return acc;
  }, {} as Record<string, ComplianceRequirement[]>);

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="max-w-6xl mx-auto space-y-8">
        {Object.entries(grouped).map(([category, reqs]) => (
          <div key={category}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">{category}</h2>
              <Badge variant="outline">
                {reqs.filter((r) => r.is_addressed).length}/{reqs.length} addressed
              </Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {reqs.map((req) => (
                <div
                  key={req.id}
                  className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                    req.is_addressed
                      ? "border-accent/30 bg-accent/5"
                      : "border-border hover:border-primary/30"
                  }`}
                  onClick={() => {
                    onSelectRequirement(req);
                    onSwitchToList();
                  }}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <Badge
                      variant={
                        req.importance === "mandatory"
                          ? "destructive"
                          : req.importance === "evaluated"
                          ? "default"
                          : "secondary"
                      }
                      className="text-xs"
                    >
                      {req.importance}
                    </Badge>
                    <span className="text-xs text-muted-foreground font-mono">
                      {req.section}
                    </span>
                  </div>

                  <p className="text-sm line-clamp-3 mb-3">
                    {req.requirement_text}
                  </p>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1">
                      {req.is_addressed ? (
                        <>
                          <CheckCircle2 className="w-4 h-4 text-accent" />
                          <span className="text-xs text-accent">Addressed</span>
                        </>
                      ) : (
                        <>
                          <FileText className="w-4 h-4 text-muted-foreground" />
                          <span className="text-xs text-muted-foreground">Pending</span>
                        </>
                      )}
                    </div>

                    {!req.is_addressed && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          onGenerate(req);
                        }}
                        disabled={isGenerating && generatingId === req.id}
                      >
                        {isGenerating && generatingId === req.id ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          "Generate"
                        )}
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
