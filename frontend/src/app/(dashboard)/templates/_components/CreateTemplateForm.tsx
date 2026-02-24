"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface CreateTemplateFormProps {
  name: string;
  description: string;
  content: string;
  category: string;
  shareOnCreate: boolean;
  saving: boolean;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onContentChange: (value: string) => void;
  onCategoryChange: (value: string) => void;
  onShareOnCreateChange: (value: boolean) => void;
  onSubmit: (event: React.FormEvent) => void;
}

export function CreateTemplateForm({
  name,
  description,
  content,
  category,
  shareOnCreate,
  saving,
  onNameChange,
  onDescriptionChange,
  onContentChange,
  onCategoryChange,
  onShareOnCreateChange,
  onSubmit,
}: CreateTemplateFormProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Create Community Template</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-3" onSubmit={onSubmit}>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <input
              value={name}
              onChange={(event) => onNameChange(event.target.value)}
              placeholder="Template name"
              className="rounded-md border border-border px-3 py-2 text-sm"
              required
            />
            <select
              value={category}
              onChange={(event) => onCategoryChange(event.target.value)}
              className="rounded-md border border-border px-3 py-2 text-sm"
            >
              <option value="Proposal Structure">Proposal Structure</option>
              <option value="Compliance Matrix">Compliance Matrix</option>
              <option value="Technical">Technical</option>
              <option value="Past Performance">Past Performance</option>
            </select>
          </div>
          <input
            value={description}
            onChange={(event) => onDescriptionChange(event.target.value)}
            placeholder="Short description"
            className="w-full rounded-md border border-border px-3 py-2 text-sm"
            required
          />
          <textarea
            value={content}
            onChange={(event) => onContentChange(event.target.value)}
            placeholder="Template content"
            className="min-h-28 w-full rounded-md border border-border px-3 py-2 text-sm"
            required
          />
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={shareOnCreate}
              onChange={(event) => onShareOnCreateChange(event.target.checked)}
            />
            Share to community after creation
          </label>
          <Button type="submit" disabled={saving}>
            Create Template
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
