"use client";

import React from "react";
import {
  CheckCircle2,
  Circle,
  AlertTriangle,
  Info,
  Loader2,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn, getImportanceColor, truncate } from "@/lib/utils";
import type { ComplianceRequirement, ImportanceLevel } from "@/types";

interface ComplianceMatrixProps {
  requirements: ComplianceRequirement[];
  selectedId?: string;
  onSelect: (requirement: ComplianceRequirement) => void;
  onGenerate: (requirement: ComplianceRequirement) => void;
  isGenerating?: boolean;
  generatingId?: string;
}

const importanceIcons: Record<ImportanceLevel, React.ElementType> = {
  mandatory: AlertTriangle,
  evaluated: Info,
  optional: Circle,
  informational: Circle,
};

const importanceBadges: Record<
  ImportanceLevel,
  { label: string; variant: "destructive" | "warning" | "default" | "secondary" }
> = {
  mandatory: { label: "Mandatory", variant: "destructive" },
  evaluated: { label: "Evaluated", variant: "warning" },
  optional: { label: "Optional", variant: "default" },
  informational: { label: "Info", variant: "secondary" },
};

export function ComplianceMatrix({
  requirements,
  selectedId,
  onSelect,
  onGenerate,
  isGenerating,
  generatingId,
}: ComplianceMatrixProps) {
  const stats = {
    total: requirements.length,
    mandatory: requirements.filter((r) => r.importance === "mandatory").length,
    addressed: requirements.filter((r) => r.is_addressed).length,
  };

  return (
    <div className="split-panel">
      {/* Header */}
      <div className="split-panel-header">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-foreground">Compliance Matrix</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {stats.addressed}/{stats.total} requirements addressed
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="destructive" className="text-xs">
              {stats.mandatory} Mandatory
            </Badge>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-3 h-1.5 bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full bg-accent transition-all duration-500"
            style={{ width: `${(stats.addressed / stats.total) * 100}%` }}
          />
        </div>
      </div>

      {/* Requirements List */}
      <ScrollArea className="split-panel-content">
        <div className="p-2 space-y-1">
          {requirements.map((requirement) => {
            const isSelected = requirement.id === selectedId;
            const isThisGenerating =
              isGenerating && generatingId === requirement.id;
            const Icon = importanceIcons[requirement.importance];
            const badge = importanceBadges[requirement.importance];

            return (
              <div
                key={requirement.id}
                className={cn(
                  "group relative p-3 rounded-lg border transition-all cursor-pointer",
                  isSelected
                    ? "bg-primary/10 border-primary/50"
                    : "bg-card border-border hover:border-primary/30 hover:bg-secondary/50"
                )}
                onClick={() => onSelect(requirement)}
              >
                {/* Status indicator */}
                <div className="absolute left-0 top-0 bottom-0 w-1 rounded-l-lg">
                  <div
                    className={cn(
                      "h-full rounded-l-lg transition-colors",
                      requirement.is_addressed
                        ? "bg-accent"
                        : requirement.importance === "mandatory"
                        ? "bg-destructive"
                        : "bg-muted"
                    )}
                  />
                </div>

                <div className="flex items-start gap-3 pl-2">
                  {/* Check/Status Icon */}
                  <div className="mt-0.5">
                    {requirement.is_addressed ? (
                      <CheckCircle2 className="w-4 h-4 text-accent" />
                    ) : (
                      <Icon
                        className={cn(
                          "w-4 h-4",
                          getImportanceColor(requirement.importance)
                        )}
                      />
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono text-muted-foreground">
                        {requirement.section}
                      </span>
                      <Badge variant={badge.variant} className="text-[10px] px-1.5 py-0">
                        {badge.label}
                      </Badge>
                    </div>

                    <p className="text-sm text-foreground line-clamp-2">
                      {truncate(requirement.requirement_text, 150)}
                    </p>

                    {requirement.category && (
                      <span className="inline-block mt-1.5 text-xs text-muted-foreground">
                        {requirement.category}
                      </span>
                    )}
                  </div>

                  {/* Generate Button */}
                  <Button
                    size="sm"
                    variant={isSelected ? "default" : "ghost"}
                    className={cn(
                      "flex-shrink-0 transition-opacity",
                      !isSelected && "opacity-0 group-hover:opacity-100"
                    )}
                    onClick={(e) => {
                      e.stopPropagation();
                      onGenerate(requirement);
                    }}
                    disabled={isThisGenerating}
                  >
                    {isThisGenerating ? (
                      <>
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span className="ml-1">Writing...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3 h-3" />
                        <span className="ml-1">Generate</span>
                      </>
                    )}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}

