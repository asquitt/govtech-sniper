"use client";

import React from "react";
import { Package, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";
import type { SubmissionPackage } from "@/types";

interface SubmissionPanelProps {
  packages: SubmissionPackage[];
  title: string;
  onTitleChange: (title: string) => void;
  dueDate: string;
  onDueDateChange: (date: string) => void;
  onCreatePackage: () => void;
}

export function SubmissionPanel({
  packages,
  title,
  onTitleChange,
  dueDate,
  onDueDateChange,
  onCreatePackage,
}: SubmissionPanelProps) {
  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Package className="w-4 h-4 text-primary" />
          <p className="text-sm font-semibold">Submission Packages</p>
        </div>
        <div className="space-y-2">
          {packages.length === 0 ? (
            <p className="text-xs text-muted-foreground">No packages yet.</p>
          ) : (
            packages.map((pkg) => (
              <div key={pkg.id} className="border border-border rounded-md p-2">
                <p className="text-sm text-foreground">{pkg.title}</p>
                <p className="text-xs text-muted-foreground">
                  Status: {pkg.status}
                </p>
                {pkg.due_date && (
                  <p className="text-xs text-muted-foreground">
                    Due {formatDate(pkg.due_date)}
                  </p>
                )}
              </div>
            ))
          )}
        </div>
        <div className="space-y-2">
          <input
            className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Package title"
            value={title}
            onChange={(e) => onTitleChange(e.target.value)}
          />
          <input
            className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Due date (YYYY-MM-DD)"
            value={dueDate}
            onChange={(e) => onDueDateChange(e.target.value)}
          />
          <Button
            variant="outline"
            className="w-full"
            onClick={onCreatePackage}
          >
            <Plus className="w-4 h-4" />
            Create Package
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
