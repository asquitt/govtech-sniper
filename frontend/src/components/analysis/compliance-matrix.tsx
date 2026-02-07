"use client";

import React, { useMemo, useState } from "react";
import {
  CheckCircle2,
  Circle,
  AlertTriangle,
  Filter,
  Info,
  Loader2,
  Sparkles,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn, getImportanceColor, truncate } from "@/lib/utils";
import type { ComplianceRequirement, ImportanceLevel, RequirementStatus } from "@/types";

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

const statusBadges: Record<
  RequirementStatus,
  { label: string; variant: "default" | "success" | "warning" | "destructive" }
> = {
  open: { label: "Open", variant: "default" },
  in_progress: { label: "In Progress", variant: "warning" },
  blocked: { label: "Blocked", variant: "destructive" },
  addressed: { label: "Addressed", variant: "success" },
};

export function ComplianceMatrix({
  requirements,
  selectedId,
  onSelect,
  onGenerate,
  isGenerating,
  generatingId,
}: ComplianceMatrixProps) {
  const [sourceSectionFilter, setSourceSectionFilter] = useState<string>("all");

  // Collect unique source sections for the filter dropdown
  const sourceSections = useMemo(() => {
    const sections = new Set<string>();
    requirements.forEach((r) => {
      if (r.source_section) sections.add(r.source_section);
    });
    return Array.from(sections).sort();
  }, [requirements]);

  // Apply filter
  const filtered = useMemo(
    () =>
      sourceSectionFilter === "all"
        ? requirements
        : requirements.filter((r) => r.source_section === sourceSectionFilter),
    [requirements, sourceSectionFilter]
  );

  const stats = {
    total: requirements.length,
    mandatory: requirements.filter((r) => r.importance === "mandatory").length,
    addressed: requirements.filter((r) => r.is_addressed).length,
    filtered: filtered.length,
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
              {sourceSectionFilter !== "all" && ` (showing ${stats.filtered})`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="destructive" className="text-xs">
              {stats.mandatory} Mandatory
            </Badge>
          </div>
        </div>

        {/* Source section filter */}
        {sourceSections.length > 0 && (
          <div className="flex items-center gap-2 mt-2">
            <Filter className="w-3 h-3 text-muted-foreground" />
            <select
              value={sourceSectionFilter}
              onChange={(e) => setSourceSectionFilter(e.target.value)}
              className="text-xs bg-secondary border border-border rounded px-2 py-1 text-foreground"
            >
              <option value="all">All Sections</option>
              {sourceSections.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Progress bar */}
        <div className="mt-3 h-1.5 bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full bg-accent transition-all duration-500"
            style={{ width: `${stats.total > 0 ? (stats.addressed / stats.total) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* Requirements List */}
      <ScrollArea className="split-panel-content">
        <div className="p-2 space-y-1">
          {filtered.map((requirement) => {
            const isSelected = requirement.id === selectedId;
            const isThisGenerating =
              isGenerating && generatingId === requirement.id;
            const Icon = importanceIcons[requirement.importance];
            const badge = importanceBadges[requirement.importance];
            const status =
              requirement.status || (requirement.is_addressed ? "addressed" : "open");
            const statusBadge = statusBadges[status];

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
                      <Badge
                        variant={statusBadge.variant}
                        className="text-[10px] px-1.5 py-0"
                      >
                        {statusBadge.label}
                      </Badge>
                    </div>

                    <p className="text-sm text-foreground line-clamp-2">
                      {truncate(requirement.requirement_text, 150)}
                    </p>

                    <div className="flex items-center gap-2 mt-1.5">
                      {requirement.source_section && (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-mono">
                          {requirement.source_section}
                        </Badge>
                      )}
                      {requirement.category && (
                        <span className="text-xs text-muted-foreground">
                          {requirement.category}
                        </span>
                      )}
                    </div>

                    {requirement.assigned_to && (
                      <span className="block mt-1 text-xs text-muted-foreground">
                        Owner: {requirement.assigned_to}
                      </span>
                    )}

                    {requirement.tags && requirement.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {requirement.tags.slice(0, 3).map((tag) => (
                          <Badge
                            key={`${requirement.id}-${tag}`}
                            variant="outline"
                            className="text-[10px] px-1.5 py-0"
                          >
                            {tag}
                          </Badge>
                        ))}
                        {requirement.tags.length > 3 && (
                          <span className="text-[10px] text-muted-foreground">
                            +{requirement.tags.length - 3}
                          </span>
                        )}
                      </div>
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
