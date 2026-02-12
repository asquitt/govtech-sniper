"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { collaborationApi } from "@/lib/api";
import type { WorkspaceMember } from "@/types";

type AcceptState = "idle" | "loading" | "success" | "error";

export default function CollaborationAcceptPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token")?.trim() ?? "";
  const [state, setState] = useState<AcceptState>(token ? "loading" : "idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [membership, setMembership] = useState<WorkspaceMember | null>(null);

  const acceptInvitation = useCallback(async () => {
    if (!token) {
      setState("idle");
      return;
    }
    try {
      setState("loading");
      setErrorMessage(null);
      const member = await collaborationApi.acceptInvitation(token);
      setMembership(member);
      setState("success");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to accept invitation.";
      setErrorMessage(message);
      setState("error");
    }
  }, [token]);

  useEffect(() => {
    if (state === "loading" && token) {
      void acceptInvitation();
    }
  }, [acceptInvitation, state, token]);

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Accept Collaboration Invite"
        description="Join a shared workspace and start collaborating with your partner team."
      />

      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-xl rounded-lg border border-border bg-card p-6">
          {!token && (
            <div className="flex items-start gap-3 text-sm text-muted-foreground">
              <AlertCircle className="w-4 h-4 mt-0.5 text-destructive" />
              <div>
                <p className="font-medium text-foreground">Missing invitation token</p>
                <p className="mt-1">
                  Open the full invite link from your workspace owner to continue.
                </p>
              </div>
            </div>
          )}

          {state === "loading" && token && (
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              Accepting invitation...
            </div>
          )}

          {state === "error" && token && (
            <div className="space-y-3">
              <div className="flex items-start gap-3 text-sm text-destructive">
                <AlertCircle className="w-4 h-4 mt-0.5" />
                <div>
                  <p className="font-medium">Unable to accept invitation</p>
                  <p className="mt-1 text-muted-foreground">{errorMessage}</p>
                </div>
              </div>
              <Button onClick={() => void acceptInvitation()}>Retry</Button>
            </div>
          )}

          {state === "success" && membership && (
            <div className="space-y-4">
              <div className="flex items-start gap-3 text-sm">
                <CheckCircle2 className="w-4 h-4 mt-0.5 text-green-500" />
                <div>
                  <p className="font-medium text-foreground">Invitation accepted</p>
                  <p className="mt-1 text-muted-foreground">
                    You joined as <span className="font-medium">{membership.role}</span>.
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button asChild>
                  <Link href={`/collaboration?workspace=${membership.workspace_id}`}>
                    Go to Workspace
                  </Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href={`/collaboration/portal/${membership.workspace_id}`}>
                    Open Partner Portal
                  </Link>
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
