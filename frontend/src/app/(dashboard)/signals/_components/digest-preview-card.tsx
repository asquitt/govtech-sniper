"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SignalDigestPreview, SignalDigestSendResponse } from "@/types/signals";

export interface DigestPreviewCardProps {
  digestPreview: SignalDigestPreview;
  lastDigestSend: SignalDigestSendResponse | null;
}

export function DigestPreviewCard({ digestPreview, lastDigestSend }: DigestPreviewCardProps) {
  return (
    <Card data-testid="signals-digest-preview-card">
      <CardHeader>
        <CardTitle>Digest Preview ({digestPreview.period_days} day window)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">
          {digestPreview.included_count} of {digestPreview.total_unread} unread signals included.
        </p>
        <div className="flex gap-2 flex-wrap">
          {Object.entries(digestPreview.type_breakdown).map(([type, count]) => (
            <Badge key={type} variant="outline">
              {type}: {count}
            </Badge>
          ))}
        </div>
        {lastDigestSend && (
          <p className="text-xs text-muted-foreground">
            Last sent to {lastDigestSend.recipient_email} at{" "}
            {new Date(lastDigestSend.sent_at).toLocaleString()}.
          </p>
        )}
        <div className="space-y-2">
          {digestPreview.top_signals.map((item) => (
            <div key={item.signal_id} className="rounded border p-2">
              <p className="text-sm font-medium">{item.title}</p>
              <p className="text-xs text-muted-foreground">
                {Math.round(item.relevance_score)}% relevance
                {item.agency ? ` \u2022 ${item.agency}` : ""}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
