"use client";

import React from "react";
import { Cloud } from "lucide-react";

export default function IntegrationsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Cloud className="w-5 h-5 text-primary" />
        <h1 className="text-xl font-bold">Integrations</h1>
      </div>
      <p className="text-sm text-muted-foreground">
        Configure SharePoint sync and other integrations from individual
        proposal pages. Use the SharePoint Sync panel on each proposal to set up
        auto-sync, folder watching, and bidirectional sync.
      </p>
    </div>
  );
}
