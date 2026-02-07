"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { contactApi } from "@/lib/api";
import { ContactTable } from "@/components/contacts/contact-table";
import { ExtractButton } from "@/components/contacts/extract-button";
import { AgencyDirectory } from "@/components/contacts/agency-directory";
import type { OpportunityContact, AgencyProfile } from "@/types";

type TabKey = "contacts" | "agencies";

export default function ContactsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("contacts");
  const [contacts, setContacts] = useState<OpportunityContact[]>([]);
  const [agencies, setAgencies] = useState<AgencyProfile[]>([]);
  const [loadingContacts, setLoadingContacts] = useState(true);
  const [loadingAgencies, setLoadingAgencies] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchContacts = useCallback(async () => {
    setLoadingContacts(true);
    try {
      const data = await contactApi.list();
      setContacts(data);
      setError(null);
    } catch {
      setError("Failed to load contacts.");
    } finally {
      setLoadingContacts(false);
    }
  }, []);

  const fetchAgencies = useCallback(async () => {
    setLoadingAgencies(true);
    try {
      const data = await contactApi.listAgencies();
      setAgencies(data);
    } catch {
      // Silent
    } finally {
      setLoadingAgencies(false);
    }
  }, []);

  useEffect(() => {
    fetchContacts();
    fetchAgencies();
  }, [fetchContacts, fetchAgencies]);

  const handleDelete = async (id: number) => {
    try {
      await contactApi.remove(id);
      setContacts((prev) => prev.filter((c) => c.id !== id));
    } catch {
      setError("Failed to delete contact.");
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      <Header
        title="Contact Intelligence"
        description="Manage contacts, extract from RFPs, and build your agency directory."
      />

      <div className="flex-1 p-6 space-y-6">
        {error && (
          <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
            {error}
          </div>
        )}

        {/* Tab bar + actions */}
        <div className="flex items-center justify-between">
          <div className="flex gap-1 rounded-lg bg-muted p-1">
            <Button
              variant={activeTab === "contacts" ? "default" : "ghost"}
              size="sm"
              onClick={() => setActiveTab("contacts")}
            >
              Contacts
            </Button>
            <Button
              variant={activeTab === "agencies" ? "default" : "ghost"}
              size="sm"
              onClick={() => setActiveTab("agencies")}
            >
              Agency Directory
            </Button>
          </div>
          <ExtractButton onContactsSaved={fetchContacts} />
        </div>

        {/* Tab content */}
        {activeTab === "contacts" && (
          <ContactTable
            contacts={contacts}
            onDelete={handleDelete}
            loading={loadingContacts}
          />
        )}

        {activeTab === "agencies" && (
          <AgencyDirectory
            agencies={agencies}
            onRefresh={fetchAgencies}
            loading={loadingAgencies}
          />
        )}
      </div>
    </div>
  );
}
