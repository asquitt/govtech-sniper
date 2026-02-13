"use client";

import React, { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { captureApi } from "@/lib/api";
import type {
  TeamingPartner,
  TeamingPartnerLink,
  RFPListItem,
} from "@/types";

interface TeamingPartnersPanelProps {
  rfps: RFPListItem[];
  partners: TeamingPartner[];
  partnerLinks: TeamingPartnerLink[];
  selectedRfpId: number | null;
  onSelectRfp: (rfpId: number) => void;
  onPartnerLinksChange: (links: TeamingPartnerLink[]) => void;
  onPartnersRefresh: () => Promise<void>;
  onError: (message: string) => void;
}

export function TeamingPartnersPanel({
  rfps,
  partners,
  partnerLinks,
  selectedRfpId,
  onSelectRfp,
  onPartnerLinksChange,
  onPartnersRefresh,
  onError,
}: TeamingPartnersPanelProps) {
  const [partnerName, setPartnerName] = useState("");
  const [partnerType, setPartnerType] = useState("");
  const [linkPartnerId, setLinkPartnerId] = useState<number | null>(null);
  const [linkRole, setLinkRole] = useState("");

  const partnerById = useMemo(() => {
    const map = new Map<number, TeamingPartner>();
    partners.forEach((partner) => map.set(partner.id, partner));
    return map;
  }, [partners]);

  const handleCreatePartner = async () => {
    if (!partnerName.trim()) return;
    try {
      await captureApi.createPartner({
        name: partnerName.trim(),
        partner_type: partnerType.trim() || undefined,
      });
      setPartnerName("");
      setPartnerType("");
      await onPartnersRefresh();
    } catch (err) {
      console.error("Failed to create teaming partner", err);
      onError("Failed to create teaming partner.");
    }
  };

  const handleLinkPartner = async () => {
    if (!selectedRfpId || !linkPartnerId) return;
    try {
      await captureApi.linkPartner({
        rfp_id: selectedRfpId,
        partner_id: linkPartnerId,
        role: linkRole.trim() || undefined,
      });
      setLinkRole("");
      const linksResult = await captureApi.listPartnerLinks(selectedRfpId);
      onPartnerLinksChange(linksResult.links);
    } catch (err) {
      console.error("Failed to link partner", err);
      onError("Failed to link partner.");
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 space-y-4">
      <div>
        <p className="text-sm font-medium text-foreground">Teaming Partners</p>
        <p className="text-xs text-muted-foreground">
          Maintain partner list and link to opportunities
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <input
          className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Partner name"
          value={partnerName}
          onChange={(e) => setPartnerName(e.target.value)}
        />
        <input
          className="w-40 rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Type (prime/sub)"
          value={partnerType}
          onChange={(e) => setPartnerType(e.target.value)}
        />
        <Button onClick={handleCreatePartner}>Add Partner</Button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          value={selectedRfpId ?? ""}
          onChange={(e) => onSelectRfp(Number(e.target.value))}
        >
          {rfps.map((rfp) => (
            <option key={rfp.id} value={rfp.id}>
              {rfp.title}
            </option>
          ))}
        </select>
        <select
          className="rounded-md border border-border bg-background px-2 py-1 text-sm"
          value={linkPartnerId ?? ""}
          onChange={(e) => setLinkPartnerId(Number(e.target.value))}
        >
          <option value="">Select partner</option>
          {partners.map((partner) => (
            <option key={partner.id} value={partner.id}>
              {partner.name}
            </option>
          ))}
        </select>
        <input
          className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm"
          placeholder="Role (Subcontractor)"
          value={linkRole}
          onChange={(e) => setLinkRole(e.target.value)}
        />
        <Button onClick={handleLinkPartner}>Link</Button>
      </div>

      <div className="space-y-2">
        {partnerLinks.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No partners linked to this opportunity.
          </p>
        ) : (
          partnerLinks.map((link) => {
            const partner = partnerById.get(link.partner_id);
            return (
              <div
                key={link.id}
                className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
              >
                <div>
                  <p className="font-medium text-foreground">
                    {partner?.name || "Unknown Partner"}
                  </p>
                  {link.role && (
                    <p className="text-xs text-muted-foreground">{link.role}</p>
                  )}
                </div>
                <Badge variant="outline">
                  {partner?.partner_type || "Partner"}
                </Badge>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
