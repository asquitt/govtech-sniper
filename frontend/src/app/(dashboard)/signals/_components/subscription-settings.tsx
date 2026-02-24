"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface SubscriptionSettingsProps {
  keywords: string;
  digestEnabled: boolean;
  digestFrequency: "daily" | "weekly";
  onKeywordsChange: (value: string) => void;
  onDigestEnabledChange: (value: boolean) => void;
  onDigestFrequencyChange: (value: "daily" | "weekly") => void;
  onSave: () => void;
}

export function SubscriptionSettings({
  keywords,
  digestEnabled,
  digestFrequency,
  onKeywordsChange,
  onDigestEnabledChange,
  onDigestFrequencyChange,
  onSave,
}: SubscriptionSettingsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Subscription Preferences</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="text-sm font-medium">Keywords (comma-separated)</label>
          <input
            className="w-full border rounded-lg px-3 py-2 text-sm bg-background mt-1"
            placeholder="cybersecurity, cloud, AI/ML"
            value={keywords}
            onChange={(e) => onKeywordsChange(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-3">
          <input
            id="signals-digest-enabled"
            type="checkbox"
            checked={digestEnabled}
            onChange={(event) => onDigestEnabledChange(event.target.checked)}
          />
          <label htmlFor="signals-digest-enabled" className="text-sm">
            Enable market signals email digest
          </label>
        </div>

        <div>
          <label className="text-sm font-medium">Digest Frequency</label>
          <select
            className="mt-1 w-full border rounded-lg px-3 py-2 text-sm bg-background"
            value={digestFrequency}
            onChange={(event) =>
              onDigestFrequencyChange(event.target.value as "daily" | "weekly")
            }
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
          </select>
        </div>

        <Button size="sm" onClick={onSave}>
          Save Preferences
        </Button>
      </CardContent>
    </Card>
  );
}
