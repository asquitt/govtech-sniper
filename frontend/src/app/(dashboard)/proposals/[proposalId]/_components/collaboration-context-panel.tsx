"use client";

import React, { useEffect, useMemo, useState } from "react";
import { MessageSquareText, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SectionLockIndicator } from "@/components/proposals/section-lock-indicator";
import { collaborationApi } from "@/lib/api/collaboration";
import { reviewApi } from "@/lib/api/reviews";
import { tokenManager } from "@/lib/api/client";
import type { DocumentPresence, ReviewComment, SectionLock } from "@/types";

interface CollaborationContextPanelProps {
  proposalId: number;
  selectedSectionId: number | null;
}

function extractCurrentUserId(): number | undefined {
  const token = tokenManager.getAccessToken();
  if (!token) return undefined;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    const parsed = Number(payload.sub);
    return Number.isFinite(parsed) ? parsed : undefined;
  } catch {
    return undefined;
  }
}

export function CollaborationContextPanel({
  proposalId,
  selectedSectionId,
}: CollaborationContextPanelProps) {
  const [presence, setPresence] = useState<DocumentPresence>({
    proposal_id: proposalId,
    users: [],
    locks: [],
  });
  const [comments, setComments] = useState<ReviewComment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const currentUserId = useMemo(() => extractCurrentUserId(), []);

  useEffect(() => {
    let mounted = true;

    const loadPresence = async () => {
      try {
        const next = await collaborationApi.getPresence(proposalId);
        if (mounted) {
          setPresence(next);
        }
      } catch (err) {
        console.error("Failed to load collaboration presence", err);
      }
    };

    loadPresence();
    const interval = setInterval(loadPresence, 8000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [proposalId]);

  useEffect(() => {
    let mounted = true;

    const loadInlineComments = async () => {
      if (!selectedSectionId) {
        setComments([]);
        return;
      }
      try {
        const next = await reviewApi.getInlineComments(selectedSectionId);
        if (mounted) {
          setComments(next);
        }
      } catch (err) {
        console.error("Failed to load inline comments", err);
      }
    };

    loadInlineComments();
    return () => {
      mounted = false;
    };
  }, [selectedSectionId]);

  const sectionLock: SectionLock | null = selectedSectionId
    ? presence.locks.find((item) => item.section_id === selectedSectionId) || null
    : null;

  const handleLock = async () => {
    if (!selectedSectionId) return;
    setError(null);
    try {
      await collaborationApi.lockSection(selectedSectionId);
      const next = await collaborationApi.getPresence(proposalId);
      setPresence(next);
    } catch (err) {
      console.error("Failed to lock section", err);
      setError("Section is already locked by another collaborator.");
    }
  };

  const handleUnlock = async () => {
    if (!selectedSectionId) return;
    setError(null);
    try {
      await collaborationApi.unlockSection(selectedSectionId);
      const next = await collaborationApi.getPresence(proposalId);
      setPresence(next);
    } catch (err) {
      console.error("Failed to unlock section", err);
      setError("Unable to release lock for this section.");
    }
  };

  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-primary" />
            <p className="text-sm font-semibold">Collaboration Context</p>
          </div>
          <Badge variant="outline">{presence.users.length} active collaborators</Badge>
        </div>

        {selectedSectionId ? (
          <SectionLockIndicator
            lock={sectionLock}
            currentUserId={currentUserId}
            onLock={handleLock}
            onUnlock={handleUnlock}
          />
        ) : (
          <p className="text-xs text-muted-foreground">
            Select a section to manage edit locks.
          </p>
        )}

        {error ? <p className="text-xs text-destructive">{error}</p> : null}

        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <MessageSquareText className="w-4 h-4 text-primary" />
            <p className="text-sm font-semibold">Inline Review Comments</p>
            <Badge variant="secondary">{comments.length}</Badge>
          </div>
          {comments.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No inline comments for the selected section.
            </p>
          ) : (
            <div className="space-y-2">
              {comments.slice(0, 5).map((comment) => (
                <div
                  key={comment.id}
                  className="rounded-md border border-border bg-background/40 px-2 py-1.5 text-xs"
                >
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant="outline">{comment.severity}</Badge>
                    <Badge variant="secondary">{comment.status}</Badge>
                  </div>
                  <p className="mt-1 text-foreground">{comment.comment_text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
