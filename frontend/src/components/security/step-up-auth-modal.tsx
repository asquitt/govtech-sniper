"use client";

import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

interface StepUpAuthModalProps {
  open: boolean;
  title?: string;
  description?: string;
  isSubmitting?: boolean;
  error?: string | null;
  onSubmit: (code: string) => Promise<void> | void;
  onClose: () => void;
}

export function StepUpAuthModal({
  open,
  title = "Step-Up Authentication Required",
  description = "Enter your current 6-digit MFA code to continue.",
  isSubmitting = false,
  error = null,
  onSubmit,
  onClose,
}: StepUpAuthModalProps) {
  const [code, setCode] = useState("");

  useEffect(() => {
    if (open) {
      setCode("");
    }
  }, [open]);

  if (!open) return null;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!code.trim()) return;
    await onSubmit(code.trim());
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">{description}</p>
          <form className="space-y-3" onSubmit={handleSubmit}>
            <Input
              aria-label="Step-up authentication code"
              inputMode="numeric"
              pattern="[0-9]*"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="123456"
            />
            {error ? <p className="text-xs text-destructive">{error}</p> : null}
            <div className="flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isSubmitting}
                onClick={onClose}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isSubmitting || !code.trim()}>
                {isSubmitting ? "Verifying..." : "Verify"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
