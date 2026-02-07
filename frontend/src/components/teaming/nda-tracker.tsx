"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileText, Plus } from "lucide-react";
import type { NDAStatus, TeamingNDA } from "@/types";
import { teamingBoardApi } from "@/lib/api/teaming";

interface NDATrackerProps {
  partnerId?: number;
  onCreateNDA?: () => void;
}

const STATUS_COLORS: Record<NDAStatus, string> = {
  draft: "bg-muted text-muted-foreground",
  sent: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  signed: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  expired: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

const NEXT_STATUS: Partial<Record<NDAStatus, NDAStatus>> = {
  draft: "sent",
  sent: "signed",
};

export function NDATracker({ partnerId, onCreateNDA }: NDATrackerProps) {
  const [ndas, setNDAs] = useState<TeamingNDA[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await teamingBoardApi.listNDAs(
        partnerId ? { partner_id: partnerId } : undefined,
      );
      setNDAs(data);
    } catch (err) {
      console.error("Failed to load NDAs", err);
    } finally {
      setLoading(false);
    }
  }, [partnerId]);

  useEffect(() => {
    load();
  }, [load]);

  const advanceStatus = async (nda: TeamingNDA) => {
    const next = NEXT_STATUS[nda.status as NDAStatus];
    if (!next) return;
    try {
      const updated = await teamingBoardApi.updateNDA(nda.id, {
        status: next,
        ...(next === "signed" ? { signed_date: new Date().toISOString().slice(0, 10) } : {}),
      });
      setNDAs((prev) => prev.map((n) => (n.id === updated.id ? updated : n)));
    } catch (err) {
      console.error("Failed to update NDA", err);
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-sm">
          <FileText className="w-4 h-4" />
          NDA Tracking
        </CardTitle>
        {onCreateNDA && (
          <Button size="sm" variant="outline" onClick={onCreateNDA}>
            <Plus className="w-3.5 h-3.5 mr-1" />
            New NDA
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground animate-pulse">Loading NDAs...</p>
        ) : ndas.length === 0 ? (
          <p className="text-sm text-muted-foreground">No NDAs tracked yet.</p>
        ) : (
          <div className="space-y-2">
            {ndas.map((nda) => (
              <div
                key={nda.id}
                className="flex items-center justify-between rounded-lg border border-border p-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Partner #{nda.partner_id}</span>
                    <Badge className={STATUS_COLORS[nda.status as NDAStatus] ?? ""}>
                      {nda.status}
                    </Badge>
                  </div>
                  <div className="flex gap-3 text-xs text-muted-foreground">
                    {nda.signed_date && <span>Signed: {nda.signed_date}</span>}
                    {nda.expiry_date && <span>Expires: {nda.expiry_date}</span>}
                  </div>
                  {nda.notes && (
                    <p className="text-xs text-muted-foreground">{nda.notes}</p>
                  )}
                </div>
                {NEXT_STATUS[nda.status as NDAStatus] && (
                  <Button size="sm" variant="outline" onClick={() => advanceStatus(nda)}>
                    Mark {NEXT_STATUS[nda.status as NDAStatus]}
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
