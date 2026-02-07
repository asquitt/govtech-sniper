"use client";

import React, { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { rfpApi } from "@/lib/api";
import { useDashStore } from "@/lib/stores/dash-store";
import type { RFPListItem } from "@/types";

export function ContextSelector() {
  const [opportunities, setOpportunities] = useState<RFPListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { selectedRfpId, setSelectedRfpId } = useDashStore();

  useEffect(() => {
    const load = async () => {
      try {
        const list = await rfpApi.list({ limit: 50 });
        setOpportunities(list);
        if (list.length > 0 && !selectedRfpId) {
          setSelectedRfpId(list[0].id);
        }
      } catch (err) {
        console.error("Failed to load opportunities", err);
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="border-b border-border px-4 py-3">
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <p className="text-xs font-medium text-muted-foreground mb-1">Opportunity Context</p>
          <div className="flex items-center gap-2">
            <select
              className="flex-1 rounded-md border border-border bg-background px-2 py-1.5 text-sm"
              value={selectedRfpId ?? ""}
              onChange={(e) => setSelectedRfpId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">No opportunity selected</option>
              {opportunities.map((rfp) => (
                <option key={rfp.id} value={rfp.id}>
                  {rfp.title}
                </option>
              ))}
            </select>
            {isLoading && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
            {selectedRfpId && <Badge variant="outline">ID {selectedRfpId}</Badge>}
          </div>
        </div>
      </div>
    </div>
  );
}
