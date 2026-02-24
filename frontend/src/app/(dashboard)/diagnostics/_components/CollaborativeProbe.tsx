"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CursorPosition, DocumentPresenceUser, SectionLock } from "@/types";

interface CollaborativeProbeProps {
  proposalId: string;
  sectionId: string;
  participantName: string;
  onProposalIdChange: (value: string) => void;
  onSectionIdChange: (value: string) => void;
  onParticipantNameChange: (value: string) => void;
  onSendMessage: (payload: Record<string, unknown>) => void;
  presenceUsers: DocumentPresenceUser[];
  locks: SectionLock[];
  cursors: CursorPosition[];
}

export function CollaborativeProbe({
  proposalId,
  sectionId,
  participantName,
  onProposalIdChange,
  onSectionIdChange,
  onParticipantNameChange,
  onSendMessage,
  presenceUsers,
  locks,
  cursors,
}: CollaborativeProbeProps) {
  const parsedProposalId = Number(proposalId) || 0;
  const parsedSectionId = Number(sectionId) || 0;

  return (
    <Card className="border border-border">
      <CardHeader>
        <CardTitle>Collaborative Probe</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
          <label className="text-xs text-muted-foreground">
            Proposal ID
            <input
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
              value={proposalId}
              onChange={(event) => onProposalIdChange(event.target.value)}
            />
          </label>
          <label className="text-xs text-muted-foreground">
            Section ID
            <input
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
              value={sectionId}
              onChange={(event) => onSectionIdChange(event.target.value)}
            />
          </label>
          <label className="text-xs text-muted-foreground">
            User label
            <input
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
              value={participantName}
              onChange={(event) => onParticipantNameChange(event.target.value)}
            />
          </label>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              onSendMessage({
                type: "join_document",
                proposal_id: parsedProposalId,
                user_name: participantName,
              })
            }
          >
            Join Document
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              onSendMessage({
                type: "leave_document",
                proposal_id: parsedProposalId,
              })
            }
          >
            Leave Document
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              onSendMessage({
                type: "lock_section",
                proposal_id: parsedProposalId,
                section_id: parsedSectionId,
                user_name: participantName,
              })
            }
          >
            Lock Section
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              onSendMessage({
                type: "unlock_section",
                proposal_id: parsedProposalId,
                section_id: parsedSectionId,
              })
            }
          >
            Unlock Section
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              onSendMessage({
                type: "cursor_update",
                proposal_id: parsedProposalId,
                section_id: parsedSectionId,
                user_name: participantName,
                position: Math.floor(Math.random() * 1000),
              })
            }
          >
            Send Cursor
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="rounded-md border border-border p-3 space-y-1">
            <p className="font-medium text-foreground">Presence Users</p>
            {presenceUsers.length === 0 ? (
              <p className="text-muted-foreground">No users joined.</p>
            ) : (
              presenceUsers.map((user) => (
                <p key={user.user_id} className="text-muted-foreground">
                  {user.user_name} ({user.user_id})
                </p>
              ))
            )}
          </div>
          <div className="rounded-md border border-border p-3 space-y-1">
            <p className="font-medium text-foreground">Section Locks</p>
            {locks.length === 0 ? (
              <p className="text-muted-foreground">No active locks.</p>
            ) : (
              locks.map((lock) => (
                <p key={`${lock.section_id}-${lock.user_id}`} className="text-muted-foreground">
                  Section {lock.section_id} by {lock.user_name}
                </p>
              ))
            )}
          </div>
          <div className="rounded-md border border-border p-3 space-y-1">
            <p className="font-medium text-foreground">Cursor Telemetry</p>
            {cursors.length === 0 ? (
              <p className="text-muted-foreground">No cursor updates.</p>
            ) : (
              cursors.map((cursor) => (
                <p
                  key={`${cursor.user_id}-${cursor.section_id ?? "none"}`}
                  className="text-muted-foreground"
                >
                  {cursor.user_name} @ section {cursor.section_id ?? "-"} pos {cursor.position}
                </p>
              ))
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
