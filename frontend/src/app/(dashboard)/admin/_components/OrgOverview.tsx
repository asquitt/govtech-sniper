"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Building2, Shield, Globe, Users } from "lucide-react";
import type { OrganizationDetails } from "@/types";

interface OrgOverviewProps {
  org: OrganizationDetails | null;
  loading: boolean;
}

export function OrgOverview({ org, loading }: OrgOverviewProps) {
  if (loading || !org) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="border border-border">
            <CardContent className="p-4">
              <div className="animate-pulse space-y-2">
                <div className="h-4 w-20 bg-muted rounded" />
                <div className="h-6 w-16 bg-muted rounded" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const cards = [
    {
      icon: Building2,
      label: "Organization",
      value: org.name,
      sub: org.slug,
    },
    {
      icon: Users,
      label: "Members",
      value: org.member_count.toString(),
      sub: "Active users",
    },
    {
      icon: Shield,
      label: "SSO",
      value: org.sso_enabled ? "Enabled" : "Disabled",
      sub: org.sso_provider ?? "Not configured",
    },
    {
      icon: Globe,
      label: "Domain",
      value: org.domain ?? "Not set",
      sub: org.sso_enforce ? "SSO enforced" : "Password login allowed",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {cards.map((card) => (
        <Card key={card.label} className="border border-border">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <card.icon className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">{card.label}</span>
            </div>
            <p className="text-lg font-semibold text-foreground">{card.value}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{card.sub}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
