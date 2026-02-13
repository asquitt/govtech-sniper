"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { contactApi } from "@/lib/api";
import type { OpportunityContact } from "@/types";

interface ContactsSectionProps {
  rfpId: number;
  initialContacts: OpportunityContact[];
  onError: (message: string) => void;
}

export function ContactsSection({ rfpId, initialContacts, onError }: ContactsSectionProps) {
  const [contacts, setContacts] = useState<OpportunityContact[]>(initialContacts);
  const [isSavingContact, setIsSavingContact] = useState(false);
  const [contactForm, setContactForm] = useState({
    name: "",
    role: "",
    organization: "",
    email: "",
    phone: "",
    notes: "",
  });

  const handleContactChange = (field: keyof typeof contactForm, value: string) => {
    setContactForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreateContact = async () => {
    if (!contactForm.name.trim()) return;
    try {
      setIsSavingContact(true);
      const payload = {
        rfp_id: rfpId,
        name: contactForm.name.trim(),
        role: contactForm.role || undefined,
        organization: contactForm.organization || undefined,
        email: contactForm.email || undefined,
        phone: contactForm.phone || undefined,
        notes: contactForm.notes || undefined,
      };
      const created = await contactApi.create(payload);
      setContacts((prev) => [created, ...prev]);
      setContactForm({
        name: "",
        role: "",
        organization: "",
        email: "",
        phone: "",
        notes: "",
      });
    } catch (err) {
      console.error("Failed to create contact", err);
      onError("Failed to create contact.");
    } finally {
      setIsSavingContact(false);
    }
  };

  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Opportunity Contacts</p>
            <p className="text-xs text-muted-foreground">
              Track buyers, stakeholders, and partner contacts.
            </p>
          </div>
          <Button
            size="sm"
            onClick={handleCreateContact}
            disabled={isSavingContact}
          >
            {isSavingContact ? "Saving..." : "Add Contact"}
          </Button>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Name"
            value={contactForm.name}
            onChange={(e) => handleContactChange("name", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Role"
            value={contactForm.role}
            onChange={(e) => handleContactChange("role", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Organization"
            value={contactForm.organization}
            onChange={(e) => handleContactChange("organization", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Email"
            value={contactForm.email}
            onChange={(e) => handleContactChange("email", e.target.value)}
          />
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            placeholder="Phone"
            value={contactForm.phone}
            onChange={(e) => handleContactChange("phone", e.target.value)}
          />
        </div>

        <textarea
          className="min-h-[80px] rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Contact notes"
          value={contactForm.notes}
          onChange={(e) => handleContactChange("notes", e.target.value)}
        />

        {contacts.length === 0 ? (
          <p className="text-sm text-muted-foreground">No contacts yet.</p>
        ) : (
          <div className="space-y-2">
            {contacts.map((contact) => (
              <div
                key={contact.id}
                className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
              >
                <div>
                  <p className="font-medium text-foreground">{contact.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {contact.role || "Role unknown"} · {contact.organization || "Org"}
                  </p>
                </div>
                <Badge variant="outline">
                  {contact.email || contact.phone || "No contact info"}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
