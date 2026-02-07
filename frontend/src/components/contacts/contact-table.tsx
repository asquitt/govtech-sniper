"use client";

import React, { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Search, Trash2, Mail, Phone } from "lucide-react";
import type { OpportunityContact } from "@/types";

interface ContactTableProps {
  contacts: OpportunityContact[];
  onDelete: (id: number) => void;
  loading?: boolean;
}

export function ContactTable({ contacts, onDelete, loading }: ContactTableProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");

  const filtered = contacts.filter((c) => {
    const matchesSearch =
      !searchQuery ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.agency?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.organization?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesSource = sourceFilter === "all" || c.source === sourceFilter;
    return matchesSearch && matchesSource;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        Loading contacts...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            className="w-full border rounded-lg pl-9 pr-3 py-2 text-sm bg-background"
            placeholder="Search contacts..."
            value={searchQuery}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
          />
        </div>
        <select
          className="border rounded-lg px-3 py-2 text-sm bg-background"
          value={sourceFilter}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSourceFilter(e.target.value)}
        >
          <option value="all">All Sources</option>
          <option value="manual">Manual</option>
          <option value="ai_extracted">AI Extracted</option>
          <option value="imported">Imported</option>
        </select>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          No contacts found.
        </div>
      ) : (
        <div className="rounded-md border overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left px-4 py-3 font-medium">Name</th>
                <th className="text-left px-4 py-3 font-medium">Title / Role</th>
                <th className="text-left px-4 py-3 font-medium">Agency</th>
                <th className="text-left px-4 py-3 font-medium">Contact Info</th>
                <th className="text-left px-4 py-3 font-medium">Source</th>
                <th className="w-[60px] px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((contact) => (
                <tr key={contact.id} className="border-b hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium">{contact.name}</td>
                  <td className="px-4 py-3">
                    <div className="space-y-0.5">
                      {contact.title && <div>{contact.title}</div>}
                      {contact.role && (
                        <div className="text-xs text-muted-foreground">{contact.role}</div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="space-y-0.5">
                      {contact.agency && <div>{contact.agency}</div>}
                      {contact.department && (
                        <div className="text-xs text-muted-foreground">{contact.department}</div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1">
                      {contact.email && (
                        <a
                          href={`mailto:${contact.email}`}
                          className="text-primary hover:underline flex items-center gap-1"
                        >
                          <Mail className="w-3 h-3" />
                          {contact.email}
                        </a>
                      )}
                      {contact.phone && (
                        <span className="flex items-center gap-1 text-muted-foreground">
                          <Phone className="w-3 h-3" />
                          {contact.phone}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <SourceBadge source={contact.source} confidence={contact.extraction_confidence} />
                  </td>
                  <td className="px-4 py-3">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onDelete(contact.id)}
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SourceBadge({
  source,
  confidence,
}: {
  source?: string | null;
  confidence?: number | null;
}) {
  const variant =
    source === "ai_extracted"
      ? "secondary"
      : source === "imported"
        ? "outline"
        : "default";

  const label =
    source === "ai_extracted"
      ? "AI"
      : source === "imported"
        ? "Imported"
        : "Manual";

  return (
    <div className="flex items-center gap-1">
      <Badge variant={variant} className="text-xs">
        {label}
      </Badge>
      {source === "ai_extracted" && confidence != null && (
        <span className="text-xs text-muted-foreground">
          {Math.round(confidence * 100)}%
        </span>
      )}
    </div>
  );
}
