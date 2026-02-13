"use client";

import React, { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { analysisApi } from "@/lib/api";
import type { ComplianceRequirement } from "@/types";

interface EditFormState {
  section: string;
  requirement_text: string;
  importance: string;
  category: string;
  notes: string;
  is_addressed: boolean;
  page_reference: string;
  keywords: string;
  status: string;
  assigned_to: string;
  tags: string;
}

export function initEditForm(req: ComplianceRequirement): EditFormState {
  return {
    section: req.section,
    requirement_text: req.requirement_text,
    importance: req.importance,
    category: req.category || "",
    notes: req.notes || "",
    is_addressed: req.is_addressed,
    page_reference: req.page_reference ? String(req.page_reference) : "",
    keywords: req.keywords?.join(", ") || "",
    status: req.status || (req.is_addressed ? "addressed" : "open"),
    assigned_to: req.assigned_to || "",
    tags: req.tags?.join(", ") || "",
  };
}

interface EditRequirementFormProps {
  rfpId: number;
  requirement: ComplianceRequirement;
  initialForm: EditFormState;
  onSaved: (requirements: ComplianceRequirement[], updated?: ComplianceRequirement) => void;
  onDeleted: () => void;
  onCancel: () => void;
  onError: (msg: string) => void;
}

const inputClass =
  "mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm";

export function EditRequirementForm({
  rfpId,
  requirement,
  initialForm,
  onSaved,
  onDeleted,
  onCancel,
  onError,
}: EditRequirementFormProps) {
  const [editForm, setEditForm] = useState<EditFormState>(initialForm);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    try {
      setIsSaving(true);
      const payload = {
        section: editForm.section,
        requirement_text: editForm.requirement_text,
        importance: editForm.importance as ComplianceRequirement["importance"],
        category: editForm.category || undefined,
        notes: editForm.notes || undefined,
        is_addressed: editForm.is_addressed,
        page_reference: editForm.page_reference
          ? parseInt(editForm.page_reference, 10)
          : undefined,
        keywords: editForm.keywords
          ? editForm.keywords.split(",").map((k) => k.trim()).filter(Boolean)
          : [],
        status: editForm.status as ComplianceRequirement["status"],
        assigned_to: editForm.assigned_to || undefined,
        tags: editForm.tags
          ? editForm.tags.split(",").map((k) => k.trim()).filter(Boolean)
          : [],
      } satisfies Partial<ComplianceRequirement>;
      const updated = await analysisApi.updateRequirement(rfpId, requirement.id, payload);
      const refreshed = updated.requirements.find((req) => req.id === requirement.id);
      onSaved(updated.requirements, refreshed);
    } catch (err) {
      console.error("Failed to save requirement", err);
      onError("Failed to save requirement changes.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await analysisApi.deleteRequirement(rfpId, requirement.id);
      onDeleted();
    } catch (err) {
      console.error("Failed to delete requirement", err);
      onError("Failed to delete requirement.");
    }
  };

  return (
    <div className="px-6 pt-4">
      <Card className="border border-border">
        <CardContent className="p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-foreground">
                Edit Requirement {requirement.id}
              </p>
              <p className="text-xs text-muted-foreground">
                Update compliance metadata and notes
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={onCancel}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleDelete}>
                <Trash2 className="w-4 h-4" />
                Delete
              </Button>
              <Button onClick={handleSave} disabled={isSaving}>
                <Pencil className="w-4 h-4" />
                Save
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-muted-foreground">Section</label>
              <input
                className={inputClass}
                value={editForm.section}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, section: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Importance</label>
              <select
                className={inputClass}
                value={editForm.importance}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, importance: e.target.value }))
                }
              >
                <option value="mandatory">Mandatory</option>
                <option value="evaluated">Evaluated</option>
                <option value="optional">Optional</option>
                <option value="informational">Informational</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Category</label>
              <input
                className={inputClass}
                value={editForm.category}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, category: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Status</label>
              <select
                className={inputClass}
                value={editForm.status}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, status: e.target.value }))
                }
              >
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="blocked">Blocked</option>
                <option value="addressed">Addressed</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Assigned To</label>
              <input
                className={inputClass}
                value={editForm.assigned_to}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, assigned_to: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Page Reference</label>
              <input
                className={inputClass}
                value={editForm.page_reference}
                onChange={(e) =>
                  setEditForm((prev) => ({
                    ...prev,
                    page_reference: e.target.value,
                  }))
                }
              />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-muted-foreground">Requirement Text</label>
              <textarea
                className={`${inputClass} min-h-[120px]`}
                value={editForm.requirement_text}
                onChange={(e) =>
                  setEditForm((prev) => ({
                    ...prev,
                    requirement_text: e.target.value,
                  }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Keywords (comma separated)</label>
              <input
                className={inputClass}
                value={editForm.keywords}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, keywords: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Tags (comma separated)</label>
              <input
                className={inputClass}
                value={editForm.tags}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, tags: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Notes</label>
              <input
                className={inputClass}
                value={editForm.notes}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, notes: e.target.value }))
                }
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={editForm.is_addressed}
                onChange={(e) =>
                  setEditForm((prev) => ({
                    ...prev,
                    is_addressed: e.target.checked,
                    status: e.target.checked
                      ? "addressed"
                      : prev.status === "addressed"
                      ? "open"
                      : prev.status,
                  }))
                }
              />
              <span className="text-sm text-muted-foreground">
                Mark as addressed
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
