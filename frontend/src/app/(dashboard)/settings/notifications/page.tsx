"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { notificationApi } from "@/lib/api";
import type { PushSubscriptionRecord } from "@/lib/api";

function randomToken(length = 32): string {
  const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  let token = "";
  for (let i = 0; i < length; i += 1) {
    token += chars[Math.floor(Math.random() * chars.length)];
  }
  return token;
}

export default function NotificationSettingsPage() {
  const [permission, setPermission] = useState<NotificationPermission>("default");
  const [subscriptions, setSubscriptions] = useState<PushSubscriptionRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadSubscriptions = useCallback(async () => {
    try {
      const rows = await notificationApi.listPushSubscriptions();
      setSubscriptions(rows);
    } catch {
      setError("Failed to load push subscriptions.");
    }
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window) {
      setPermission(Notification.permission);
    }
    loadSubscriptions();
  }, [loadSubscriptions]);

  const requestPermission = async () => {
    if (!("Notification" in window)) {
      setError("This browser does not support notifications.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      if (result !== "granted") {
        return;
      }

      await notificationApi.createPushSubscription({
        endpoint: `browser://${window.location.host}/${Date.now()}`,
        p256dh_key: randomToken(64),
        auth_key: randomToken(32),
        user_agent: navigator.userAgent,
      });
      await loadSubscriptions();
    } catch {
      setError("Failed to enable browser push notifications.");
    } finally {
      setSaving(false);
    }
  };

  const removeSubscription = async (id: number) => {
    try {
      await notificationApi.deletePushSubscription(id);
      await loadSubscriptions();
    } catch {
      setError("Failed to remove subscription.");
    }
  };

  const permissionBadgeVariant =
    permission === "granted" ? "success" : permission === "denied" ? "destructive" : "outline";

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Notification Settings"
        description="Manage browser push notifications and device subscriptions"
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {error && <p className="text-sm text-destructive">{error}</p>}

        <Card className="border border-border">
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-foreground">Browser Push Notifications</p>
                <p className="text-xs text-muted-foreground">
                  Enable push alerts for opportunity changes and deadlines.
                </p>
              </div>
              <Badge variant={permissionBadgeVariant}>{permission}</Badge>
            </div>

            <Button onClick={requestPermission} disabled={saving}>
              {saving ? "Enabling..." : "Enable Push Notifications"}
            </Button>
          </CardContent>
        </Card>

        <Card className="border border-border">
          <CardContent className="p-4 space-y-3">
            <p className="text-sm font-medium text-foreground">Registered Devices</p>
            {subscriptions.length === 0 ? (
              <p className="text-xs text-muted-foreground">No push subscriptions yet.</p>
            ) : (
              subscriptions.map((subscription) => (
                <div
                  key={subscription.id}
                  className="rounded-md border border-border p-3 flex items-center justify-between gap-3"
                >
                  <div className="min-w-0">
                    <p className="text-xs text-foreground truncate">{subscription.endpoint}</p>
                    <p className="text-[11px] text-muted-foreground truncate">
                      {subscription.user_agent || "Unknown device"}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    onClick={() => removeSubscription(subscription.id)}
                  >
                    Remove
                  </Button>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
