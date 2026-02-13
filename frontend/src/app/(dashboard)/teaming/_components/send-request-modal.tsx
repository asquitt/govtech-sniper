"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface SendRequestModalProps {
  requestMessage: string;
  onMessageChange: (value: string) => void;
  onSend: () => void;
  onCancel: () => void;
}

export function SendRequestModal({
  requestMessage,
  onMessageChange,
  onSend,
  onCancel,
}: SendRequestModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Send Teaming Request</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <textarea
            className="w-full border rounded-lg px-3 py-2 text-sm bg-background min-h-[100px]"
            placeholder="Include a message (optional)"
            value={requestMessage}
            onChange={(e) => onMessageChange(e.target.value)}
          />
          <div className="flex gap-2 justify-end">
            <Button variant="outline" size="sm" onClick={onCancel}>
              Cancel
            </Button>
            <Button size="sm" onClick={onSend}>
              Send Request
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
