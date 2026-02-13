"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { captureApi } from "@/lib/api";
import type {
  CaptureStage,
  CaptureCustomField,
  CaptureFieldType,
  CaptureFieldValue,
  CapturePlanListItem,
} from "@/types";

const stageOptions: { value: CaptureStage; label: string }[] = [
  { value: "identified", label: "Identified" },
  { value: "qualified", label: "Qualified" },
  { value: "pursuit", label: "Pursuit" },
  { value: "proposal", label: "Proposal" },
  { value: "submitted", label: "Submitted" },
  { value: "won", label: "Won" },
  { value: "lost", label: "Lost" },
];

interface CustomFieldsPanelProps {
  plan: CapturePlanListItem | undefined;
  planFieldValues: CaptureFieldValue[];
  onFieldValuesChange: (values: CaptureFieldValue[]) => void;
  onFieldsChange: (
    updater: (prev: CaptureCustomField[]) => CaptureCustomField[]
  ) => void;
  onError: (message: string) => void;
}

export function CustomFieldsPanel({
  plan,
  planFieldValues,
  onFieldValuesChange,
  onFieldsChange,
  onError,
}: CustomFieldsPanelProps) {
  const [customFieldName, setCustomFieldName] = useState("");
  const [customFieldType, setCustomFieldType] =
    useState<CaptureFieldType>("text");
  const [customFieldOptions, setCustomFieldOptions] = useState("");
  const [customFieldStage, setCustomFieldStage] = useState<
    CaptureStage | ""
  >("");
  const [customFieldRequired, setCustomFieldRequired] = useState(false);
  const [isSavingFields, setIsSavingFields] = useState(false);

  const handleFieldValueChange = (fieldId: number, value: unknown) => {
    onFieldValuesChange(
      planFieldValues.map((item) =>
        item.field.id === fieldId ? { ...item, value } : item
      )
    );
  };

  const handleSavePlanFields = async () => {
    if (!plan) return;
    try {
      setIsSavingFields(true);
      const updated = await captureApi.savePlanFields(
        plan.id,
        planFieldValues
      );
      onFieldValuesChange(updated.fields);
    } catch (err) {
      console.error("Failed to save custom fields", err);
      onError("Failed to save custom fields.");
    } finally {
      setIsSavingFields(false);
    }
  };

  const handleCreateCustomField = async () => {
    if (!customFieldName.trim()) return;
    try {
      const options =
        customFieldType === "select"
          ? customFieldOptions
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean)
          : [];
      const field = await captureApi.createField({
        name: customFieldName.trim(),
        field_type: customFieldType,
        options,
        stage: customFieldStage || null,
        is_required: customFieldRequired,
      });
      onFieldsChange((prev) => [...prev, field]);
      setCustomFieldName("");
      setCustomFieldOptions("");
      setCustomFieldStage("");
      setCustomFieldRequired(false);
    } catch (err) {
      console.error("Failed to create custom field", err);
      onError("Failed to create custom field.");
    }
  };

  const renderFieldControl = (item: CaptureFieldValue) => {
    const value = item.value ?? "";
    if (item.field.field_type === "select") {
      return (
        <select
          className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
          value={String(value)}
          onChange={(e) =>
            handleFieldValueChange(item.field.id, e.target.value)
          }
        >
          <option value="">Select option</option>
          {item.field.options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      );
    }

    if (item.field.field_type === "boolean") {
      return (
        <select
          className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
          value={value === "" ? "" : String(value)}
          onChange={(e) =>
            handleFieldValueChange(
              item.field.id,
              e.target.value === "" ? "" : e.target.value === "true"
            )
          }
        >
          <option value="">Select</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      );
    }

    return (
      <input
        className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
        type={item.field.field_type === "date" ? "date" : "text"}
        value={String(value)}
        onChange={(e) =>
          handleFieldValueChange(
            item.field.id,
            item.field.field_type === "number"
              ? Number(e.target.value)
              : e.target.value
          )
        }
      />
    );
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 space-y-4 mt-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-foreground">Custom Fields</p>
          <p className="text-xs text-muted-foreground">
            Add capture-specific fields and set values per opportunity.
          </p>
        </div>
        <Button
          size="sm"
          onClick={handleSavePlanFields}
          disabled={isSavingFields}
        >
          {isSavingFields ? "Saving..." : "Save Values"}
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Field name"
          value={customFieldName}
          onChange={(e) => setCustomFieldName(e.target.value)}
        />
        <select
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          value={customFieldType}
          onChange={(e) =>
            setCustomFieldType(e.target.value as CaptureFieldType)
          }
        >
          <option value="text">Text</option>
          <option value="number">Number</option>
          <option value="select">Select</option>
          <option value="date">Date</option>
          <option value="boolean">Boolean</option>
        </select>
        <input
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Options (comma-separated)"
          value={customFieldOptions}
          onChange={(e) => setCustomFieldOptions(e.target.value)}
          disabled={customFieldType !== "select"}
        />
        <select
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          value={customFieldStage}
          onChange={(e) =>
            setCustomFieldStage(e.target.value as CaptureStage | "")
          }
        >
          <option value="">Any Stage</option>
          {stageOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            checked={customFieldRequired}
            onChange={(e) => setCustomFieldRequired(e.target.checked)}
          />
          Required
        </label>
        <Button onClick={handleCreateCustomField}>Add Field</Button>
      </div>

      <div className="space-y-3">
        {planFieldValues.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No custom fields available for this plan.
          </p>
        ) : (
          planFieldValues.map((item) => (
            <div
              key={item.field.id}
              className="grid grid-cols-3 gap-3 items-center text-sm"
            >
              <div>
                <p className="font-medium text-foreground">
                  {item.field.name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {item.field.field_type}{" "}
                  {item.field.is_required ? "\u00b7 Required" : ""}
                </p>
              </div>
              <div className="col-span-2">{renderFieldControl(item)}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
