"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Building2, Globe, MapPin, Plus, Loader2 } from "lucide-react";
import { contactApi } from "@/lib/api";
import type { AgencyProfile } from "@/types";

interface AgencyDirectoryProps {
  agencies: AgencyProfile[];
  onRefresh: () => void;
  loading?: boolean;
}

export function AgencyDirectory({ agencies, onRefresh, loading }: AgencyDirectoryProps) {
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [agencyName, setAgencyName] = useState("");
  const [office, setOffice] = useState("");
  const [website, setWebsite] = useState("");
  const [address, setAddress] = useState("");

  const handleCreate = async () => {
    if (!agencyName.trim()) return;
    setSaving(true);
    try {
      await contactApi.upsertAgency({
        agency_name: agencyName.trim(),
        office: office || undefined,
        website: website || undefined,
        address: address || undefined,
      });
      setAgencyName("");
      setOffice("");
      setWebsite("");
      setAddress("");
      setShowForm(false);
      onRefresh();
    } catch {
      // Error handled silently
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        Loading agencies...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Agency Directory</h3>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowForm(!showForm)}
          className="gap-1"
        >
          <Plus className="w-4 h-4" />
          Add Agency
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardContent className="pt-4 space-y-3">
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm bg-background"
              placeholder="Agency name *"
              value={agencyName}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAgencyName(e.target.value)}
            />
            <div className="grid grid-cols-2 gap-3">
              <input
                className="border rounded-lg px-3 py-2 text-sm bg-background"
                placeholder="Office / Division"
                value={office}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setOffice(e.target.value)}
              />
              <input
                className="border rounded-lg px-3 py-2 text-sm bg-background"
                placeholder="Website"
                value={website}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setWebsite(e.target.value)}
              />
            </div>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm bg-background"
              placeholder="Address"
              value={address}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAddress(e.target.value)}
            />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleCreate}
                disabled={!agencyName.trim() || saving}
              >
                {saving && <Loader2 className="w-4 h-4 animate-spin mr-1" />}
                Save
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {agencies.length === 0 && !showForm ? (
        <div className="text-center py-12 text-muted-foreground">
          No agencies in directory. Add one to get started.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agencies.map((agency) => (
            <Card key={agency.id}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-primary" />
                  {agency.agency_name}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm text-muted-foreground">
                {agency.office && <div>{agency.office}</div>}
                {agency.address && (
                  <div className="flex items-center gap-1">
                    <MapPin className="w-3 h-3" />
                    {agency.address}
                  </div>
                )}
                {agency.website && (
                  <div className="flex items-center gap-1">
                    <Globe className="w-3 h-3" />
                    <a
                      href={agency.website.startsWith("http") ? agency.website : `https://${agency.website}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline truncate"
                    >
                      {agency.website}
                    </a>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
