"use client";

import React, { useState } from "react";
import { Loader2, Save, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { pastPerformanceApi } from "@/lib/api";
import type { PastPerformanceDocument, PastPerformanceMetadata } from "@/types/past-performance";

interface PerformanceMetadataFormProps {
  document: PastPerformanceDocument;
  onSaved: (updated: PastPerformanceDocument) => void;
  onCancel: () => void;
}

export function PerformanceMetadataForm({ document, onSaved, onCancel }: PerformanceMetadataFormProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tagsInput, setTagsInput] = useState(document.relevance_tags?.join(", ") || "");

  const [form, setForm] = useState<PastPerformanceMetadata>({
    contract_number: document.contract_number || "",
    performing_agency: document.performing_agency || "",
    contract_value: document.contract_value || undefined,
    period_of_performance_start: document.period_of_performance_start?.split("T")[0] || "",
    period_of_performance_end: document.period_of_performance_end?.split("T")[0] || "",
    naics_code: document.naics_code || "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setError(null);

    try {
      const tags = tagsInput
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);

      const payload: PastPerformanceMetadata = {
        ...form,
        contract_value: form.contract_value ? Number(form.contract_value) : undefined,
        period_of_performance_start: form.period_of_performance_start || undefined,
        period_of_performance_end: form.period_of_performance_end || undefined,
        relevance_tags: tags.length > 0 ? tags : undefined,
      };

      const res = await pastPerformanceApi.addMetadata(document.id, payload);
      onSaved(res.data);
    } catch (err) {
      console.error("Failed to save metadata:", err);
      setError("Failed to save metadata. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const inputClass =
    "w-full h-10 px-3 rounded-lg bg-secondary border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary";

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold">Edit Metadata: {document.title}</h3>
        <Button type="button" variant="ghost" size="icon" onClick={onCancel}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      {error && (
        <p className="text-sm text-destructive bg-destructive/10 p-2 rounded">{error}</p>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1">
            Contract Number
          </label>
          <input
            type="text"
            className={inputClass}
            placeholder="e.g., GS-35F-0001X"
            value={form.contract_number || ""}
            onChange={(e) => setForm({ ...form, contract_number: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1">
            Performing Agency
          </label>
          <input
            type="text"
            className={inputClass}
            placeholder="e.g., Department of Defense"
            value={form.performing_agency || ""}
            onChange={(e) => setForm({ ...form, performing_agency: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1">
            Contract Value ($)
          </label>
          <input
            type="number"
            className={inputClass}
            placeholder="e.g., 500000"
            value={form.contract_value ?? ""}
            onChange={(e) => setForm({ ...form, contract_value: e.target.value ? Number(e.target.value) : undefined })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1">
            NAICS Code
          </label>
          <input
            type="text"
            className={inputClass}
            placeholder="e.g., 541512"
            value={form.naics_code || ""}
            onChange={(e) => setForm({ ...form, naics_code: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1">
            Performance Start
          </label>
          <input
            type="date"
            className={inputClass}
            value={form.period_of_performance_start || ""}
            onChange={(e) => setForm({ ...form, period_of_performance_start: e.target.value })}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1">
            Performance End
          </label>
          <input
            type="date"
            className={inputClass}
            value={form.period_of_performance_end || ""}
            onChange={(e) => setForm({ ...form, period_of_performance_end: e.target.value })}
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-muted-foreground mb-1">
          Relevance Tags (comma-separated)
        </label>
        <input
          type="text"
          className={inputClass}
          placeholder="e.g., cybersecurity, cloud migration, DevOps"
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
        />
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSaving}>
          {isSaving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Save className="w-4 h-4 mr-1" />}
          Save Metadata
        </Button>
      </div>
    </form>
  );
}
