"use client";

import React, { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { analysisApi } from "@/lib/api";
import type { ComplianceRequirement } from "@/types";

interface NewRequirementState {
  section: string;
  requirement_text: string;
  importance: string;
  category: string;
  notes: string;
  page_reference: string;
  keywords: string;
  status: string;
  assigned_to: string;
  tags: string;
}

const emptyForm: NewRequirementState = {
  section: "",
  requirement_text: "",
  importance: "mandatory",
  category: "",
  notes: "",
  page_reference: "",
  keywords: "",
  status: "open",
  assigned_to: "",
  tags: "",
};

interface CreateRequirementFormProps {
  rfpId: number;
  onCreated: (requirements: ComplianceRequirement[]) => void;
  onCancel: () => void;
  onError: (msg: string) => void;
}

const inputClass =
  "mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm";

export function CreateRequirementForm({
  rfpId,
  onCreated,
  onCancel,
  onError,
}: CreateRequirementFormProps) {
  const [form, setForm] = useState<NewRequirementState>(emptyForm);
  const [isSaving, setIsSaving] = useState(false);

  const handleCreate = async () => {
    try {
      setIsSaving(true);
      const payload = {
        section: form.section,
        requirement_text: form.requirement_text,
        importance: form.importance as ComplianceRequirement["importance"],
        category: form.category || undefined,
        notes: form.notes || undefined,
        page_reference: form.page_reference
          ? parseInt(form.page_reference, 10)
          : undefined,
        keywords: form.keywords
          ? form.keywords.split(",").map((k) => k.trim()).filter(Boolean)
          : [],
        status: form.status as ComplianceRequirement["status"],
        assigned_to: form.assigned_to || undefined,
        tags: form.tags
          ? form.tags.split(",").map((k) => k.trim()).filter(Boolean)
          : [],
      } satisfies Partial<ComplianceRequirement>;
      const updated = await analysisApi.addRequirement(rfpId, payload);
      onCreated(updated.requirements);
    } catch (err) {
      console.error("Failed to create requirement", err);
      onError("Failed to add requirement.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="px-6 pt-4">
      <Card className="border border-border">
        <CardContent className="p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-foreground">
                Add Requirement
              </p>
              <p className="text-xs text-muted-foreground">
                Insert a new requirement into the matrix
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={onCancel}>
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={isSaving}>
                <Plus className="w-4 h-4" />
                Add
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-muted-foreground">Section</label>
              <input
                className={inputClass}
                value={form.section}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, section: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Importance</label>
              <select
                className={inputClass}
                value={form.importance}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, importance: e.target.value }))
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
                value={form.category}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, category: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Status</label>
              <select
                className={inputClass}
                value={form.status}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, status: e.target.value }))
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
                value={form.assigned_to}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, assigned_to: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Page Reference</label>
              <input
                className={inputClass}
                value={form.page_reference}
                onChange={(e) =>
                  setForm((prev) => ({
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
                value={form.requirement_text}
                onChange={(e) =>
                  setForm((prev) => ({
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
                value={form.keywords}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, keywords: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Tags (comma separated)</label>
              <input
                className={inputClass}
                value={form.tags}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, tags: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Notes</label>
              <input
                className={inputClass}
                value={form.notes}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, notes: e.target.value }))
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
