"use client";

import React from "react";
import { Palette, Plus, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";
import type { ProposalSection, ProposalGraphicRequest } from "@/types";

interface GraphicsPanelProps {
  requests: ProposalGraphicRequest[];
  sections: ProposalSection[];
  title: string;
  onTitleChange: (title: string) => void;
  description: string;
  onDescriptionChange: (desc: string) => void;
  sectionId: number | null;
  onSectionIdChange: (id: number | null) => void;
  dueDate: string;
  onDueDateChange: (date: string) => void;
  onCreateRequest: () => void;
  onUpdateStatus: (id: number, status: ProposalGraphicRequest["status"]) => void;
  onRemoveRequest: (id: number) => void;
}

export function GraphicsPanel({
  requests,
  sections,
  title,
  onTitleChange,
  description,
  onDescriptionChange,
  sectionId,
  onSectionIdChange,
  dueDate,
  onDueDateChange,
  onCreateRequest,
  onUpdateStatus,
  onRemoveRequest,
}: GraphicsPanelProps) {
  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Palette className="w-4 h-4 text-primary" />
          <p className="text-sm font-semibold">Graphics Requests</p>
        </div>
        <div className="space-y-2">
          {requests.length === 0 ? (
            <p className="text-xs text-muted-foreground">No graphics requests yet.</p>
          ) : (
            requests.map((request) => (
              <div key={request.id} className="border border-border rounded-md p-2 space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm text-foreground">{request.title}</p>
                    {request.section_id && (
                      <p className="text-xs text-muted-foreground">
                        Section {request.section_id}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground">
                      Status: {request.status}
                    </p>
                    {request.due_date && (
                      <p className="text-xs text-muted-foreground">
                        Due {formatDate(request.due_date)}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onRemoveRequest(request.id)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
                <select
                  className="w-full rounded-md border border-border bg-background px-2 py-1 text-xs"
                  value={request.status}
                  onChange={(e) =>
                    onUpdateStatus(
                      request.id,
                      e.target.value as ProposalGraphicRequest["status"]
                    )
                  }
                >
                  <option value="requested">Requested</option>
                  <option value="in_progress">In Progress</option>
                  <option value="delivered">Delivered</option>
                  <option value="rejected">Rejected</option>
                </select>
              </div>
            ))
          )}
        </div>
        <div className="space-y-2">
          <input
            className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Graphic title"
            value={title}
            onChange={(e) => onTitleChange(e.target.value)}
          />
          <textarea
            className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Description or layout guidance"
            value={description}
            onChange={(e) => onDescriptionChange(e.target.value)}
            rows={3}
          />
          <select
            className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
            value={sectionId ?? ""}
            onChange={(e) => onSectionIdChange(Number(e.target.value) || null)}
          >
            <option value="">Link to section (optional)</option>
            {sections.map((section) => (
              <option key={section.id} value={section.id}>
                {section.section_number} {section.title}
              </option>
            ))}
          </select>
          <input
            className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Due date (YYYY-MM-DD)"
            value={dueDate}
            onChange={(e) => onDueDateChange(e.target.value)}
          />
          <Button
            variant="outline"
            className="w-full"
            onClick={onCreateRequest}
          >
            <Plus className="w-4 h-4" />
            Create Request
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
