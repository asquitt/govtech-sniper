"use client";

import React, { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { rfpApi } from "@/lib/api";
import { getApiErrorMessage } from "@/lib/api/error";
import type { DataClassification } from "@/types";

interface CreateRfpFormProps {
  onCreated: () => void;
  onCancel: () => void;
  onError: (message: string) => void;
}

interface NewRfpData {
  title: string;
  solicitation_number: string;
  agency: string;
  jurisdiction: string;
  currency: string;
  classification: DataClassification;
  response_deadline: string;
  description: string;
}

const EMPTY_RFP: NewRfpData = {
  title: "",
  solicitation_number: "",
  agency: "",
  jurisdiction: "US",
  currency: "USD",
  classification: "internal",
  response_deadline: "",
  description: "",
};

export function CreateRfpForm({ onCreated, onCancel, onError }: CreateRfpFormProps) {
  const [isCreating, setIsCreating] = useState(false);
  const [newRfp, setNewRfp] = useState<NewRfpData>(EMPTY_RFP);

  const handleCancel = () => {
    setNewRfp(EMPTY_RFP);
    onCancel();
  };

  const handleCreate = async () => {
    if (
      !newRfp.title.trim() ||
      !newRfp.solicitation_number.trim() ||
      !newRfp.agency.trim()
    ) {
      onError("Title, solicitation number, and agency are required.");
      return;
    }

    try {
      setIsCreating(true);

      await rfpApi.create({
        title: newRfp.title.trim(),
        solicitation_number: newRfp.solicitation_number.trim(),
        agency: newRfp.agency.trim(),
        jurisdiction: newRfp.jurisdiction || undefined,
        currency: newRfp.currency || "USD",
        classification: newRfp.classification,
        response_deadline: newRfp.response_deadline
          ? new Date(newRfp.response_deadline).toISOString()
          : undefined,
        description: newRfp.description.trim() || undefined,
      });

      setNewRfp(EMPTY_RFP);
      onCancel();
      onCreated();
    } catch (err) {
      console.error("Failed to create RFP:", err);
      onError(getApiErrorMessage(err, "Failed to add RFP. Please try again."));
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <Card className="border border-border mb-4">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Add Opportunity Manually</p>
            <p className="text-xs text-muted-foreground">
              Use this when SAM.gov is unavailable or for non-SAM opportunities.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleCancel}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleCreate}
              disabled={isCreating}
            >
              {isCreating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                "Save RFP"
              )}
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <label className="text-sm text-muted-foreground">
            Title
            <input
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
              value={newRfp.title}
              onChange={(e) =>
                setNewRfp((prev) => ({ ...prev, title: e.target.value }))
              }
            />
          </label>
          <label className="text-sm text-muted-foreground">
            Solicitation Number
            <input
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
              value={newRfp.solicitation_number}
              onChange={(e) =>
                setNewRfp((prev) => ({
                  ...prev,
                  solicitation_number: e.target.value,
                }))
              }
            />
          </label>
          <label className="text-sm text-muted-foreground">
            Agency
            <input
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
              value={newRfp.agency}
              onChange={(e) =>
                setNewRfp((prev) => ({ ...prev, agency: e.target.value }))
              }
            />
          </label>
          <label className="text-sm text-muted-foreground">
            Jurisdiction
            <select
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
              value={newRfp.jurisdiction}
              onChange={(e) =>
                setNewRfp((prev) => ({ ...prev, jurisdiction: e.target.value }))
              }
            >
              <option value="US">United States</option>
              <option value="CA">Canada</option>
              <option value="CA-AB">Canada - Alberta</option>
              <option value="CA-BC">Canada - British Columbia</option>
              <option value="CA-MB">Canada - Manitoba</option>
              <option value="CA-NB">Canada - New Brunswick</option>
              <option value="CA-NL">Canada - Newfoundland and Labrador</option>
              <option value="CA-NS">Canada - Nova Scotia</option>
              <option value="CA-NT">Canada - Northwest Territories</option>
              <option value="CA-NU">Canada - Nunavut</option>
              <option value="CA-ON">Canada - Ontario</option>
              <option value="CA-PE">Canada - Prince Edward Island</option>
              <option value="CA-QC">Canada - Quebec</option>
              <option value="CA-SK">Canada - Saskatchewan</option>
              <option value="CA-YT">Canada - Yukon</option>
            </select>
          </label>
          <label className="text-sm text-muted-foreground">
            Currency
            <select
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
              value={newRfp.currency}
              onChange={(e) =>
                setNewRfp((prev) => ({ ...prev, currency: e.target.value }))
              }
            >
              <option value="USD">USD</option>
              <option value="CAD">CAD</option>
            </select>
          </label>
          <label className="text-sm text-muted-foreground">
            Classification
            <select
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
              value={newRfp.classification}
              onChange={(e) =>
                setNewRfp((prev) => ({
                  ...prev,
                  classification: e.target.value as DataClassification,
                }))
              }
            >
              <option value="public">Public</option>
              <option value="internal">Internal</option>
              <option value="fci">FCI</option>
              <option value="cui">CUI</option>
            </select>
          </label>
          <label className="text-sm text-muted-foreground">
            Response Deadline
            <input
              type="date"
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
              value={newRfp.response_deadline}
              onChange={(e) =>
                setNewRfp((prev) => ({
                  ...prev,
                  response_deadline: e.target.value,
                }))
              }
            />
          </label>
        </div>

        <label className="text-sm text-muted-foreground block">
          Description
          <textarea
            className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground"
            rows={3}
            value={newRfp.description}
            onChange={(e) =>
              setNewRfp((prev) => ({
                ...prev,
                description: e.target.value,
              }))
            }
          />
        </label>
      </CardContent>
    </Card>
  );
}
