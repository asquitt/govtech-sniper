"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Sparkles, Plus, Loader2, X } from "lucide-react";
import { contactApi } from "@/lib/api";
import type { ExtractedContact, OpportunityContact } from "@/types";

interface ExtractButtonProps {
  onContactsSaved: () => void;
}

export function ExtractButton({ onContactsSaved }: ExtractButtonProps) {
  const [open, setOpen] = useState(false);
  const [rfpId, setRfpId] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [results, setResults] = useState<ExtractedContact[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleExtract = async () => {
    const id = parseInt(rfpId, 10);
    if (!id) return;

    setExtracting(true);
    setError(null);
    setResults([]);
    try {
      const extracted = await contactApi.extract(id);
      setResults(extracted);
      if (extracted.length === 0) {
        setError("No contacts found in this RFP.");
      }
    } catch {
      setError("Failed to extract contacts. Check the RFP ID and try again.");
    } finally {
      setExtracting(false);
    }
  };

  const handleSaveContact = async (contact: ExtractedContact) => {
    setSaving(true);
    try {
      await contactApi.create({
        name: contact.name,
        title: contact.title ?? undefined,
        email: contact.email ?? undefined,
        phone: contact.phone ?? undefined,
        agency: contact.agency ?? undefined,
        role: contact.role ?? undefined,
        rfp_id: parseInt(rfpId, 10) || undefined,
        source: "ai_extracted",
      } as Partial<OpportunityContact>);
      setResults((prev) => prev.filter((c) => c.name !== contact.name));
      onContactsSaved();
    } catch {
      setError("Failed to save contact.");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAll = async () => {
    setSaving(true);
    try {
      for (const contact of results) {
        await contactApi.create({
          name: contact.name,
          title: contact.title ?? undefined,
          email: contact.email ?? undefined,
          phone: contact.phone ?? undefined,
          agency: contact.agency ?? undefined,
          role: contact.role ?? undefined,
          rfp_id: parseInt(rfpId, 10) || undefined,
          source: "ai_extracted",
        } as Partial<OpportunityContact>);
      }
      setResults([]);
      onContactsSaved();
      setOpen(false);
    } catch {
      setError("Failed to save some contacts.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Button variant="outline" className="gap-2" onClick={() => setOpen(true)}>
        <Sparkles className="w-4 h-4" />
        Extract from RFP
      </Button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card border rounded-xl shadow-lg w-full max-w-lg mx-4 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">AI Contact Extraction</h3>
              <Button variant="ghost" size="icon" onClick={() => setOpen(false)} className="h-8 w-8">
                <X className="w-4 h-4" />
              </Button>
            </div>

            <div className="flex gap-2">
              <input
                className="flex-1 border rounded-lg px-3 py-2 text-sm bg-background"
                placeholder="Enter RFP ID"
                value={rfpId}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRfpId(e.target.value)}
                type="number"
              />
              <Button onClick={handleExtract} disabled={!rfpId || extracting}>
                {extracting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Extract"}
              </Button>
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            {results.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">
                    {results.length} contact{results.length !== 1 ? "s" : ""} found
                  </span>
                  <Button size="sm" onClick={handleSaveAll} disabled={saving}>
                    {saving && <Loader2 className="w-4 h-4 animate-spin mr-1" />}
                    Save All
                  </Button>
                </div>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {results.map((c, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between p-3 rounded-lg border bg-card"
                    >
                      <div>
                        <div className="font-medium text-sm">{c.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {[c.title, c.agency, c.role].filter(Boolean).join(" - ")}
                        </div>
                        {c.email && (
                          <div className="text-xs text-muted-foreground">{c.email}</div>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleSaveContact(c)}
                        disabled={saving}
                        className="h-8 w-8"
                      >
                        <Plus className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
