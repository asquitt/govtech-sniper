"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Bell, Forward, Mail } from "lucide-react";
import type { InboxMessageType } from "@/types";

export function MessageTypeBadge({ type }: { type: InboxMessageType }) {
  const config: Record<InboxMessageType, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
    general: { label: "General", variant: "secondary" },
    opportunity_alert: { label: "Opportunity", variant: "default" },
    rfp_forward: { label: "RFP Forward", variant: "outline" },
  };
  const { label, variant } = config[type] ?? config.general;
  return <Badge variant={variant}>{label}</Badge>;
}

export function MessageTypeIcon({ type }: { type: InboxMessageType }) {
  switch (type) {
    case "opportunity_alert":
      return <Bell className="w-4 h-4 text-blue-500" />;
    case "rfp_forward":
      return <Forward className="w-4 h-4 text-purple-500" />;
    default:
      return <Mail className="w-4 h-4 text-muted-foreground" />;
  }
}
